### Usage
Provide the iam user names as a space separated list <br>
bye\_bye.sh user1 [user1 [user3... [userN]]]
<br>

Does the following
1) Remove all sns subsctipions by the user
2) Remove the Opsworks user profile
3) Remove all access keys added by the user (dependency for remove iam user)
4) Deactivate the MFA device (dependency for remove iam user)
5) Delete IAM user
