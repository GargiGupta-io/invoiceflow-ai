{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:Get*Configuration",
        "s3:GetBucket*",
        "s3:ListBucket",
        "s3:ListBucketVersions"
      ],
      "Resource": [
        "arn:aws:s3:::__RESOURCE_PREFIX__-*",
        "arn:aws:s3:::__STATE_BUCKET_NAME__"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "s3:GetObject",
      "Resource": [
        "arn:aws:s3:::__RESOURCE_PREFIX__-*/*",
        "arn:aws:s3:::__STATE_BUCKET_NAME__/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:CreateDistribution",
        "cloudfront:TagResource"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Application": "__PROJECT_NAME__",
          "aws:RequestTag/Environment": "__ENVIRONMENT__"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:AuthorizeSecurityGroupIngress"
      ],
      "Resource": "arn:aws:ec2:__AWS_REGION__:__ACCOUNT_ID__:security-group-rule/*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Application": "__PROJECT_NAME__",
          "aws:RequestTag/Environment": "__ENVIRONMENT__",
          "aws:RequestTag/ManagedBy": "Terraform"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "ec2:CreateTags",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Application": "__PROJECT_NAME__",
          "aws:RequestTag/Environment": "__ENVIRONMENT__",
          "aws:RequestTag/ManagedBy": "Terraform",
          "ec2:CreateAction": [
            "CreateInternetGateway",
            "CreateRouteTable",
            "CreateSecurityGroup",
            "CreateSubnet",
            "CreateVpc",
            "CreateVpcEndpoint"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudfront:GetDistribution",
        "cloudfront:GetDistributionConfig",
        "cloudfront:ListTagsForResource",
        "cloudfront:TagResource",
        "cloudfront:UntagResource",
        "cloudfront:UpdateDistribution"
      ],
      "Resource": "arn:aws:cloudfront::__ACCOUNT_ID__:distribution/*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Application": "__PROJECT_NAME__",
          "aws:ResourceTag/Environment": "__ENVIRONMENT__"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:CreateInternetGateway",
        "ec2:CreateRouteTable",
        "ec2:CreateSecurityGroup",
        "ec2:CreateSubnet",
        "ec2:CreateVpc",
        "ec2:CreateVpcEndpoint"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Application": "__PROJECT_NAME__",
          "aws:RequestTag/Environment": "__ENVIRONMENT__",
          "aws:RequestTag/ManagedBy": "Terraform"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2:AssociateRouteTable",
        "ec2:AttachInternetGateway",
        "ec2:AuthorizeSecurityGroupEgress",
        "ec2:AuthorizeSecurityGroupIngress",
        "ec2:CreateRoute",
        "ec2:CreateRouteTable",
        "ec2:CreateSecurityGroup",
        "ec2:CreateSubnet",
        "ec2:CreateTags",
        "ec2:CreateVpcEndpoint",
        "ec2:DeleteTags",
        "ec2:ModifySubnetAttribute",
        "ec2:ModifyVpcAttribute",
        "ec2:ModifyVpcEndpoint",
        "ec2:RevokeSecurityGroupEgress",
        "ec2:RevokeSecurityGroupIngress"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "ec2:ResourceTag/Application": "__PROJECT_NAME__",
          "ec2:ResourceTag/Environment": "__ENVIRONMENT__",
          "ec2:ResourceTag/ManagedBy": "Terraform"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:CreateBucket",
        "s3:PutBucketOwnershipControls",
        "s3:PutBucketPolicy",
        "s3:PutBucketPublicAccessBlock",
        "s3:PutBucketTagging",
        "s3:PutBucketVersioning",
        "s3:PutEncryptionConfiguration",
        "s3:PutLifecycleConfiguration",
        "s3:PutObject"
      ],
      "Resource": [
        "arn:aws:s3:::__RESOURCE_PREFIX__-*",
        "arn:aws:s3:::__RESOURCE_PREFIX__-*/*",
        "arn:aws:s3:::__STATE_BUCKET_NAME__",
        "arn:aws:s3:::__STATE_BUCKET_NAME__/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable",
        "dynamodb:DeleteItem",
        "dynamodb:DeleteTable",
        "dynamodb:DescribeContinuousBackups",
        "dynamodb:DescribeTable",
        "dynamodb:DescribeTimeToLive",
        "dynamodb:GetItem",
        "dynamodb:ListTagsOfResource",
        "dynamodb:PutItem",
        "dynamodb:TagResource",
        "dynamodb:UntagResource",
        "dynamodb:UpdateContinuousBackups",
        "dynamodb:UpdateTable"
      ],
      "Resource": "arn:aws:dynamodb:__AWS_REGION__:__ACCOUNT_ID__:table/__STATE_LOCK_TABLE_NAME__"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sqs:CreateQueue",
        "sqs:SetQueueAttributes",
        "sqs:TagQueue",
        "sqs:UntagQueue"
      ],
      "Resource": "arn:aws:sqs:__AWS_REGION__:__ACCOUNT_ID__:__RESOURCE_PREFIX__-*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "rds:AddTagsToResource",
        "rds:CreateDBInstance",
        "rds:CreateDBSubnetGroup",
        "rds:ModifyDBInstance",
        "rds:ModifyDBSubnetGroup",
        "rds:RemoveTagsFromResource"
      ],
      "Resource": [
        "arn:aws:rds:__AWS_REGION__:__ACCOUNT_ID__:db:__RESOURCE_PREFIX__-*",
        "arn:aws:rds:__AWS_REGION__:__ACCOUNT_ID__:subgrp:__RESOURCE_PREFIX__-*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository",
        "ecr:PutImageScanningConfiguration",
        "ecr:PutImageTagMutability",
        "ecr:PutLifecyclePolicy",
        "ecr:TagResource",
        "ecr:UntagResource"
      ],
      "Resource": "arn:aws:ecr:__AWS_REGION__:__ACCOUNT_ID__:repository/__RESOURCE_PREFIX__*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster",
        "ecs:CreateService",
        "ecs:TagResource",
        "ecs:UntagResource",
        "ecs:UpdateClusterSettings",
        "ecs:UpdateService"
      ],
      "Resource": [
        "arn:aws:ecs:__AWS_REGION__:__ACCOUNT_ID__:cluster/__RESOURCE_PREFIX__*",
        "arn:aws:ecs:__AWS_REGION__:__ACCOUNT_ID__:service/__RESOURCE_PREFIX__*/*",
        "arn:aws:ecs:__AWS_REGION__:__ACCOUNT_ID__:task-definition/__RESOURCE_PREFIX__-*:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:RegisterTaskDefinition",
        "ecs:TagResource"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Application": "__PROJECT_NAME__",
          "aws:RequestTag/Environment": "__ENVIRONMENT__",
          "aws:RequestTag/ManagedBy": "Terraform"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:AddTags",
        "elasticloadbalancing:Create*",
        "elasticloadbalancing:Modify*",
        "elasticloadbalancing:RemoveTags",
        "elasticloadbalancing:Set*"
      ],
      "Resource": [
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:loadbalancer/app/__RESOURCE_PREFIX__-*/*",
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:targetgroup/__RESOURCE_PREFIX__-*/*",
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:listener/*/__RESOURCE_PREFIX__-*/*/*",
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:listener-rule/*/__RESOURCE_PREFIX__-*/*/*/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iam:CreateRole",
      "Resource": "arn:aws:iam::__ACCOUNT_ID__:role/__RESOURCE_PREFIX__-*",
      "Condition": {
        "ArnEquals": {
          "iam:PermissionsBoundary": "arn:aws:iam::__ACCOUNT_ID__:policy/__TASK_BOUNDARY_POLICY_NAME__"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "iam:PutRolePolicy",
        "iam:TagRole",
        "iam:UntagRole",
        "iam:UpdateAssumeRolePolicy"
      ],
      "Resource": "arn:aws:iam::__ACCOUNT_ID__:role/__RESOURCE_PREFIX__-*"
    },
    {
      "Effect": "Allow",
      "Action": "iam:AttachRolePolicy",
      "Resource": "arn:aws:iam::__ACCOUNT_ID__:role/__RESOURCE_PREFIX__-*",
      "Condition": {
        "ArnEquals": {
          "iam:PolicyARN": [
            "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy",
            "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "iam:PassRole",
      "Resource": "arn:aws:iam::__ACCOUNT_ID__:role/__RESOURCE_PREFIX__-*",
      "Condition": {
        "StringEquals": {
          "iam:PassedToService": [
            "ecs-tasks.amazonaws.com",
            "lambda.amazonaws.com"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": "iam:CreateServiceLinkedRole",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "iam:AWSServiceName": [
            "ecs.amazonaws.com",
            "ecs.application-autoscaling.amazonaws.com",
            "elasticloadbalancing.amazonaws.com",
            "rds.amazonaws.com"
          ]
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:AddPermission",
        "lambda:CreateFunction",
        "lambda:TagResource",
        "lambda:UntagResource",
        "lambda:UpdateFunctionCode",
        "lambda:UpdateFunctionConfiguration"
      ],
      "Resource": "arn:aws:lambda:__AWS_REGION__:__ACCOUNT_ID__:function:__RESOURCE_PREFIX__-*"
    },
    {
      "Effect": "Allow",
      "Action": "cognito-idp:CreateUserPool",
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/Application": "__PROJECT_NAME__",
          "aws:RequestTag/Environment": "__ENVIRONMENT__",
          "aws:RequestTag/ManagedBy": "Terraform"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:CreateResourceServer",
        "cognito-idp:CreateUserPoolClient",
        "cognito-idp:CreateUserPoolDomain",
        "cognito-idp:TagResource",
        "cognito-idp:UntagResource",
        "cognito-idp:UpdateResourceServer",
        "cognito-idp:UpdateUserPool",
        "cognito-idp:UpdateUserPoolClient"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "aws:ResourceTag/Application": "__PROJECT_NAME__",
          "aws:ResourceTag/Environment": "__ENVIRONMENT__",
          "aws:ResourceTag/ManagedBy": "Terraform"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:TagResource",
        "cloudwatch:PutMetricAlarm",
        "cloudwatch:UntagResource",
        "logs:CreateLogGroup",
        "logs:PutRetentionPolicy",
        "logs:TagResource",
        "logs:UntagResource",
        "sns:CreateTopic",
        "sns:SetTopicAttributes",
        "sns:Subscribe",
        "sns:TagResource",
        "sns:UntagResource"
      ],
      "Resource": [
        "arn:aws:cloudwatch:__AWS_REGION__:__ACCOUNT_ID__:alarm:__RESOURCE_PREFIX__-*",
        "arn:aws:logs:__AWS_REGION__:__ACCOUNT_ID__:log-group:/aws/lambda/__RESOURCE_PREFIX__-*:*",
        "arn:aws:logs:__AWS_REGION__:__ACCOUNT_ID__:log-group:/ecs/__RESOURCE_PREFIX__/*:*",
        "arn:aws:sns:__AWS_REGION__:__ACCOUNT_ID__:__RESOURCE_PREFIX__-*",
        "arn:aws:sns:__AWS_REGION__:__ACCOUNT_ID__:__RESOURCE_PREFIX__-*:*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "application-autoscaling:PutScalingPolicy",
        "application-autoscaling:RegisterScalableTarget"
      ],
      "Resource": "*",
      "Condition": {
        "StringEquals": {
          "application-autoscaling:service-namespace": "ecs"
        }
      }
    },
    {
      "Effect": "Allow",
      "Action": [
        "budgets:ListTagsForResource",
        "budgets:ModifyBudget",
        "budgets:TagResource",
        "budgets:UntagResource",
        "budgets:ViewBudget"
      ],
      "Resource": "*"
    }
  ]
}
