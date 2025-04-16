from datetime import datetime
from aws_cdk import Stack, RemovalPolicy
from constructs import Construct
from aws_cdk.aws_lambda import Function, Runtime, Code, Alias, VersionOptions
from aws_cdk.aws_apigateway import LambdaRestApi, StageOptions
from aws_cdk.aws_cloudwatch import Alarm, ComparisonOperator
from aws_cdk.aws_codedeploy import LambdaDeploymentGroup, LambdaDeploymentConfig
from aws_cdk import aws_iam as iam

class CdkWorkshopStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        environment_type = self.node.try_get_context("environmentType")
        context = self.node.try_get_context(environment_type)
        self.alias_name = context["lambda"]["alias"]
        self.stage_name = context["lambda"]["stage"]
        current_date =  datetime.today().strftime('%d-%m-%Y')



        my_lambda = Function(
            scope = self,
            id = "MyFunction",
            function_name= context["lambda"]["name"],
            handler = "handler.lambda_handler",
            runtime = Runtime.PYTHON_3_11,
            code = Code.from_asset("lambda"),
            current_version_options = VersionOptions(
                description = f'Version deployed on {current_date}',
                removal_policy = RemovalPolicy.RETAIN
            )
        )

        new_version = my_lambda.current_version
        new_version.apply_removal_policy(RemovalPolicy.RETAIN)

        alias = Alias(
            scope = self,
            id = "FunctionAlias",
            alias_name = self.alias_name,
            version = new_version
        )

        LambdaRestApi(
            scope = self,
            id = "RestAPI",
            handler = alias,
            deploy_options = StageOptions(stage_name=self.stage_name)
        )

        failure_alarm = Alarm(
            scope = self,
            id = "FunctionFailureAlarm",
            metric = alias.metric_errors(),
            threshold = 1,
            evaluation_periods = 1,
            alarm_description = "The latest deployment errors > 0",
            alarm_name = f'{self.stack_name}-canary-alarm',
            comparison_operator = ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        )

        codedeploy_role = iam.Role(
            self, "CanaryDeploymentServiceRole",
            assumed_by=iam.ServicePrincipal(f"codedeploy.{self.region}.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSCodeDeployRoleForLambdaLimited"
                )
            ]
        )

        LambdaDeploymentGroup(
            scope = self,
            id = "CanaryDeployment",
            alias = alias,
            deployment_config = LambdaDeploymentConfig.CANARY_10_PERCENT_5_MINUTES,
            alarms = [failure_alarm],
            role = codedeploy_role
        )
