{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "elasticloadbalancing:DeleteListener",
        "elasticloadbalancing:DeleteLoadBalancer",
        "elasticloadbalancing:DeleteRule"
      ],
      "Resource": [
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:loadbalancer/app/__RESOURCE_PREFIX__-*/*",
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:listener/*/__RESOURCE_PREFIX__-*/*/*",
        "arn:aws:elasticloadbalancing:__AWS_REGION__:__ACCOUNT_ID__:listener-rule/*/__RESOURCE_PREFIX__-*/*/*/*"
      ]
    }
  ]
}
