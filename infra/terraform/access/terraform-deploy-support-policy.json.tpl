{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "application-autoscaling:Describe*",
        "cloudfront:ListDistributions",
        "cloudwatch:DescribeAlarms",
        "cloudwatch:ListTagsForResource",
        "cognito-idp:Describe*",
        "cognito-idp:List*",
        "ec2:Describe*",
        "ec2:GetManagedPrefixListEntries",
        "ec2:GetSecurityGroupsForVpc",
        "ecr:Describe*",
        "ecr:Get*",
        "ecr:List*",
        "ecs:Describe*",
        "ecs:List*",
        "elasticloadbalancing:Describe*",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:List*",
        "lambda:Get*",
        "lambda:ListTags",
        "lambda:ListVersionsByFunction",
        "logs:DescribeLogGroups",
        "logs:ListTagsForResource",
        "rds:Describe*",
        "rds:ListTagsForResource",
        "s3:ListAllMyBuckets",
        "secretsmanager:DescribeSecret",
        "sns:Get*",
        "sns:List*",
        "sqs:GetQueue*",
        "sqs:List*",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "kms:DescribeKey",
      "Resource": "arn:aws:kms:__AWS_REGION__:__ACCOUNT_ID__:key/*",
      "Condition": {
        "ForAnyValue:StringEquals": {
          "kms:ResourceAliases": [
            "alias/aws/rds",
            "alias/aws/secretsmanager"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:CreateSecret",
        "secretsmanager:TagResource"
      ],
      "Resource": "arn:aws:secretsmanager:__AWS_REGION__:__ACCOUNT_ID__:secret:rds!*"
    }
  ]
}
