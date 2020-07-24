#!/bin/bash
#
if [ "$#" -lt 1 ]; then
  echo "Usage: ${0##*/} user1 [user2 [user3 .. [userN]]]"
  exit 126
fi

_jq="$(which jq || echo 'not found')"
if [[ "${_js}" = "not found" ]]; then
  echo "jq not found in path"
  exit 127
fi

_aws="$(which aws || echo 'not found')"
if [[ "${_aws}" = "not found" ]]; then
  echo "aws cli not found in path"
  exit 127
fi

domain='company.com'
account_aliases="development staging production"
sts="${_aws} sts"
iam="${_aws} iam"
opsworks="${_aws} opsworks"

dev_account="$(${sts} get-caller-identity --output text --query 'Account')"

function delete_ssh_user() {
  role="$1"

  for account in ${account_aliases}; do
    aws_cross_account="${_aws} --profile ${account}-devops"
    account_number=$(${aws_cross_account} sts get-caller-identity --output text --query 'Account')
    if ${aws_cross_account} opsworks describe-user-profiles --iam-user-arns "arn:aws:sts::${account_number}:assumed-role/$account-${role}/${user}" &>/dev/null; then
      ${aws_cross_account} opsworks delete-user-profile --iam-user-arn "arn:aws:sts::${account_number}:assumed-role/$account-${role}/${user}"
    else
      echo "no ${account}-${role} user profile found"
    fi
  done
}

function delete_sns_subscriptions() {
  for account in ${account_aliases}; do
    if [ "$account" = "development" ]; then
      aws_cross_account="${_aws}"
    else
      aws_cross_account="${_aws} --profile ${account}-devops"
    fi

    for arn in $(${aws_cross_account} sns list-subscriptions --query 'Subscriptions[?Endpoint==`'${user}'@'${domain}'`].SubscriptionArn' | awk -F '"' '/arn/{ print $2 }'); do
      if [ ! -z "$arn" ]; then
        echo "Deleting ${user} from $(echo ${arn} | awk -F':' '{ print $6 }')"
        ${aws_cross_account} sns unsubscribe --subscription-arn "${arn}"
      fi
    done
  done
}

for user in $@; do
  if ${iam} get-user --user-name "${user}" &>/dev/null; then
    echo "Username: ${user}"
    dev_user_arn="arn:aws:iam::${dev_account}:user/${user}"

    # remove the login profile
    echo "removing login profile"
    ${iam} delete-login-profile --user-name "${user}"

    # detach managed policies
    echo "checking for managed policies"
    policies=$(${iam} list-attached-user-policies --user-name "${user}")

    for policy in $(echo "${policies}" | ${_jq} '.AttachedPolicies[].PolicyArn' | tr -d '"'); do
      if [ ! -z "${policy}" ]; then
        ${iam} detach-user-policy --user-name "${user}" --policy-arn "${policy}"
      fi
    done

    # remove user from all member groups
    echo "removing from all groups"
    groups=$(${iam} list-groups-for-user --user-name "${user}")

    for group in $(echo "${groups}" | ${_jq} '.Groups[].GroupName' | tr -d '"'); do
      if [ ! -z "$group" ]; then
        ${iam} remove-user-from-group --user-name "${user}" --group-name "${group}"
      fi
    done

    # remove access keys if any
    echo "removing keys if any"
    keys=$(${iam} list-access-keys --user-name "${user}")

    for key in $(echo "${keys}" | ${_jq} '.AccessKeyMetadata[].AccessKeyId' | tr -d '"'); do
      if [ ! -z "$key" ]; then
        ${iam} delete-access-key --user-name "${user}" --access-key-id "${key}"
      fi
    done

    # disable mfa
    echo "disable mfa"
    serial_number=$(${iam} list-virtual-mfa-devices | ${_jq} '.VirtualMFADevices[].SerialNumber' | grep "${user}" | tr -d '"')
    if [ ! -z serial_number ]; then
      ${iam} deactivate-mfa-device --user-name "${user}" --serial-number "${serial_number}"
    fi


    # remove user
    echo "remove iam user"
    ${iam} delete-user --user-name "${user}"
  else
    echo "User account '${user}' doesn't exist"
  fi

  # Remove Opsworks SSH user
  echo "removing opsworks user accounts if any"
  if ${opsworks} describe-user-profiles --iam-user-arns "${dev_user_arn}" &>/dev/null; then
    ${opsworks} delete-user-profile --iam-user-arn "${dev_user_arn}"
  else
    echo "no Opsworks user profile found"
  fi

  for role in "swe" "devops" "adops"; do
    delete_ssh_user "$role"
  done

  # Remove sns subscriptions
  echo "removing sns subscriptions"
  delete_sns_subscriptions

  echo "bye bye ${user}"
  echo
done
