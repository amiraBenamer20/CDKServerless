import random
from datetime import datetime
from aws_cdk import App, Environment
from aws_cdk.assertions import Template, Match
from cdk_workshop.cdk_workshop_stack import CdkWorkshopStack

contextMock = {
    "environmentType": "qa",
    "prefix": "cdk-workshop-stack",
    "account": str(random.randint(111111111111,999999999999)),
    "qa": {
        "region": "eu-west-3",
        "lambda": {
            "name": "cdk-workshop-function",
            "alias": "live",
            "stage": "qa"
        },
        "tags": {
            "App":"cdk-workshop",
            "Environment": "QA",
            "IaC": "CDK"
        }
    }
}

app = App(context=contextMock)
environment_type = app.node.try_get_context("environmentType")
environment_context = app.node.try_get_context(environment_type)
region = environment_context["region"]
tags = environment_context["tags"]
account = app.node.try_get_context("account")
stack_name = f'{app.node.try_get_context("prefix")}-{environment_type}'

stack = CdkWorkshopStack(
    app,
    stack_name,
     env = Environment(
        account = account,
        region = region
    ),
    tags=tags,
)

template = Template.from_stack(stack)

def test_lambda_function():
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
              "Statement": [
                {
                  "Action": "sts:AssumeRole",
                  "Effect": "Allow",
                  "Principal": {
                    "Service": "lambda.amazonaws.com"
                  }
                }
              ],
              "Version": "2012-10-17"
            },
            "ManagedPolicyArns": [
              {
                "Fn::Join": [
                  "",
                  [
                    "arn:",
                    {
                      "Ref": "AWS::Partition"
                    },
                    ":iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
                  ]
                ]
              }
            ]
      }
    )
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
        "Code": {
          "S3Bucket": Match.any_value(),
          "S3Key": Match.any_value()
        },
        "Role": {
          "Fn::GetAtt": [
            Match.any_value(),
            "Arn"
          ]
        },
        "FunctionName": contextMock["qa"]["lambda"]["name"],
        "Handler": "handler.lambda_handler",
        "Runtime": "python3.11"
      }
    )

def test_function_versioning():
    current_date =  datetime.today().strftime('%d-%m-%Y')

    template.has_resource_properties(
        "AWS::Lambda::Version",
        {
            "FunctionName": {
                "Ref": Match.any_value()
            },
             "Description": f'Version deployed on {current_date}'
      }
    )

    template.has_resource("AWS::Lambda::Version", {
      "Properties": {
        "FunctionName": {
          "Ref": Match.any_value()
        },
        "Description": f'Version deployed on {current_date}'
      },
      "UpdateReplacePolicy": "Retain",
      "DeletionPolicy": "Retain"
    })

    template.has_resource_properties(
        "AWS::Lambda::Alias",
        {
            "FunctionName": {
                "Ref": Match.any_value()
            },
            "FunctionVersion": {
                "Fn::GetAtt": [
                    Match.any_value(),
                    "Version"
                ]
            },
            "Name": "live"
      }
    )

def test_api_gateway():
    template.has_resource_properties(
        "AWS::ApiGateway::RestApi",
        {
            "Name": "RestAPI"
        }
    )
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
              "Statement": [
                {
                  "Action": "sts:AssumeRole",
                  "Effect": "Allow",
                  "Principal": {
                    "Service": "apigateway.amazonaws.com"
                  }
                }
              ],
              "Version": "2012-10-17"
            },
            "ManagedPolicyArns": [
              {
                "Fn::Join": [
                  "",
                  [
                    "arn:",
                    {
                      "Ref": "AWS::Partition"
                    },
                    ":iam::aws:policy/service-role/AmazonAPIGatewayPushToCloudWatchLogs"
                  ]
                ]
              }
            ]
      }
    )

    template.has_resource_properties(
        "AWS::ApiGateway::Account",
        {
            "CloudWatchRoleArn": {
              "Fn::GetAtt": [
                Match.any_value(),
                "Arn"
              ]
            }
        }
    )

    template.has_resource_properties(
        "AWS::ApiGateway::Deployment",
        {
            "RestApiId": {
                "Ref": "RestAPI1CC12F26"
            },
            "Description": "Automatically created by the RestApi construct"
        }
    )

    template.has_resource_properties(
        "AWS::ApiGateway::Stage",
        {
            "RestApiId": {
              "Ref": Match.any_value()
            },
            "DeploymentId": {
              "Ref": Match.any_value()
            },
            "StageName": contextMock["environmentType"]
        }
    )

    template.has_resource_properties(
        "AWS::ApiGateway::Resource",
        {
            "ParentId": {
              "Fn::GetAtt": [
                Match.any_value(),
                "RootResourceId"
              ]
            },
            "PathPart": "{proxy+}",
            "RestApiId": {
              "Ref": Match.any_value()
            }
        }
    )

    template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "FunctionName": {
              "Ref": Match.any_value()
            },
            "Principal": "apigateway.amazonaws.com",
            "SourceArn": {
              "Fn::Join": [
                "",
                [
                  "arn:",
                  {
                    "Ref": "AWS::Partition"
                  },
                  f':execute-api:{region}:{account}:',
                  {
                    "Ref": Match.any_value()
                  },
                  "/",
                  {
                    "Ref": Match.any_value()
                  },
                  "/*/*"
                ]
              ]
            }
        }
    )

    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {
            "HttpMethod": "ANY",
            "ResourceId": {
              "Ref": Match.any_value()
            },
            "RestApiId": {
              "Ref": Match.any_value()
            },
            "AuthorizationType": "NONE",
            "Integration": {
              "IntegrationHttpMethod": "POST",
              "Type": "AWS_PROXY",
              "Uri": {
                "Fn::Join": [
                  "",
                  [
                    "arn:",
                    {
                      "Ref": "AWS::Partition"
                    },
                    f':apigateway:{region}:lambda:path/2015-03-31/functions/',
                    {
                      "Ref": Match.any_value()
                    },
                    "/invocations"
                  ]
                ]
              }
            }
        }
    )

def test_failed_alarm():
    template.has_resource_properties(
        "AWS::CloudWatch::Alarm",
        {
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
            "EvaluationPeriods": 1,
            "AlarmDescription": "The latest deployment errors > 0",
            "AlarmName": f'{stack.stack_name}-canary-alarm',
            "Dimensions": [
              {
                "Name": "FunctionName",
                "Value": {
                  "Ref": Match.any_value()
                }
              },
              {
                "Name": "Resource",
                "Value": {
                  "Fn::Join": [
                    "",
                    [
                      {
                        "Ref": Match.any_value()
                      },
                      ":live"
                    ]
                  ]
                }
              }
            ],
            "MetricName": "Errors",
            "Namespace": "AWS/Lambda",
            "Period": 300,
            "Statistic": "Sum",
            "Threshold": 1
        }
    )

def test_canary_deployment():
    template.has_resource_properties(
        "AWS::CodeDeploy::Application",
        {
            "ComputePlatform": "Lambda"
        }
    )

    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
              "Statement": [
                {
                  "Action": "sts:AssumeRole",
                  "Effect": "Allow",
                  "Principal": {
                    "Service": f'codedeploy.{region}.amazonaws.com'
                  }
                }
              ],
              "Version": "2012-10-17"
            },
            "ManagedPolicyArns": [
              {
                "Fn::Join": [
                  "",
                  [
                    "arn:",
                    {
                      "Ref": "AWS::Partition"
                    },
                    ":iam::aws:policy/service-role/AWSCodeDeployRoleForLambdaLimited"
                  ]
                ]
              }
            ]
        }
    )

    template.has_resource_properties(
        "AWS::CodeDeploy::DeploymentGroup",
        {
            "ApplicationName": {
              "Ref": Match.any_value()
            },
            "ServiceRoleArn": {
              "Fn::GetAtt": [
                Match.any_value(),
                "Arn"
              ]
            },
            "AlarmConfiguration": {
              "Alarms": [
                {
                  "Name": {
                    "Ref": Match.any_value()
                  }
                }
              ],
              "Enabled": True
            },
            "AutoRollbackConfiguration": {
              "Enabled": True,
              "Events": [
                "DEPLOYMENT_FAILURE",
                "DEPLOYMENT_STOP_ON_ALARM"
              ]
            },
            "DeploymentConfigName": "CodeDeployDefault.LambdaCanary10Percent5Minutes",
            "DeploymentStyle": {
              "DeploymentOption": "WITH_TRAFFIC_CONTROL",
              "DeploymentType": "BLUE_GREEN"
            }
        }
    )

def test_outputs():
    template.has_output(
        "*",
        {
            "Value": {
              "Fn::Join": [
                "",
                [
                  "https://",
                  {
                    "Ref": Match.any_value()
                  },
                  f'.execute-api.{region}.',
                  {
                    "Ref": "AWS::URLSuffix"
                  },
                  "/",
                  {
                    "Ref": Match.any_value()
                  },
                  "/"
                ]
              ]
            }
        }
    )
  