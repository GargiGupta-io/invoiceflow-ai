{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ReadDatabasePassword",
      "Effect": "Allow",
      "Action": "secretsmanager:GetSecretValue",
      "Resource": "arn:aws:secretsmanager:__AWS_REGION__:__ACCOUNT_ID__:secret:rds!db-*"
    },
    {
      "Sid": "PullInvoiceFlowImages",
      "Effect": "Allow",
      "Action": [
        "ecr:BatchCheckLayerAvailability",
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer"
      ],
      "Resource": "arn:aws:ecr:__AWS_REGION__:__ACCOUNT_ID__:repository/__RESOURCE_PREFIX__*"
    },
    {
      "Sid": "AuthenticateToEcr",
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Sid": "WriteInvoiceFlowLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
        "arn:aws:logs:__AWS_REGION__:__ACCOUNT_ID__:log-group:/aws/lambda/__RESOURCE_PREFIX__-*:*",
        "arn:aws:logs:__AWS_REGION__:__ACCOUNT_ID__:log-group:/ecs/__RESOURCE_PREFIX__/*:*"
      ]
    },
    {
      "Sid": "ReadInvoiceFlowBucket",
      "Effect": "Allow",
      "Action": "s3:ListBucket",
      "Resource": "arn:aws:s3:::__RESOURCE_PREFIX__-documents-*"
    },
    {
      "Sid": "ManageInvoiceFlowDocuments",
      "Effect": "Allow",
      "Action": [
        "s3:DeleteObject",
        "s3:GetObject",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::__RESOURCE_PREFIX__-documents-*/quarantine/*",
        "arn:aws:s3:::__RESOURCE_PREFIX__-documents-*/validated/*"
      ]
    },
    {
      "Sid": "UseInvoiceFlowQueues",
      "Effect": "Allow",
      "Action": [
        "sqs:ChangeMessageVisibility",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes",
        "sqs:GetQueueUrl",
        "sqs:ReceiveMessage",
        "sqs:SendMessage"
      ],
      "Resource": "arn:aws:sqs:__AWS_REGION__:__ACCOUNT_ID__:__RESOURCE_PREFIX__-processing*"
    },
    {
      "Sid": "ProvisionTaggedReviewers",
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminCreateUser",
        "cognito-idp:AdminGetUser"
      ],
      "Resource": "arn:aws:cognito-idp:__AWS_REGION__:__ACCOUNT_ID__:userpool/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Application": "__PROJECT_NAME__",
          "aws:ResourceTag/Environment": "__ENVIRONMENT__",
          "aws:ResourceTag/ManagedBy": "Terraform"
        }
      }
    }
  ]
}
