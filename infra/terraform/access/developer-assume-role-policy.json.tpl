{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AssumeInvoiceFlowTerraformRole",
      "Effect": "Allow",
      "Action": "sts:AssumeRole",
      "Resource": "arn:aws:iam::__ACCOUNT_ID__:role/__DEPLOY_ROLE_NAME__"
    }
  ]
}
