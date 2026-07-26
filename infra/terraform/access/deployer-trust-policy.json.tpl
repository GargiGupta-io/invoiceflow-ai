{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "TrustInvoiceFlowDeveloper",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam::__ACCOUNT_ID__:user/__DEVELOPER_USER_NAME__"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
