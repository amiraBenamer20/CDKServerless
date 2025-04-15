from aws_cdk import Stack, SecretValue
from constructs import Construct
from aws_cdk.pipelines import (
    CodePipeline,
    CodePipelineSource,
    ShellStep,
    CodeBuildStep
)
 

from aws_cdk.aws_codebuild import (
    BuildEnvironment,
    LinuxBuildImage,
    ComputeType
)
from aws_cdk.pipelines import CodePipelineSource as Source
from cdk_workshop.deploy_stage import DeployStage


class PipelineStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        environment_type = self.node.try_get_context("environmentType") or "qa"
        self.context = self.node.try_get_context(environment_type)

        # GitHub as source
        self.source_stage = Source.git_hub(
            repo_string=self.context["repository"]["name"],  # e.g., "username/repo"
            branch=self.context["repository"]["branch"],
            authentication=SecretValue.secrets_manager("github-token"),  # stored in Secrets Manager

        )

        pipeline = CodePipeline(self, "Pipeline",
            pipeline_name=self.context["pipeline"]["name"],
            synth=ShellStep(
                "Synth",
                input=self.source_stage,
                env={
                    "ENV_TYPE": environment_type
                },
                install_commands=[
                    "npm install -g aws-cdk",
                    "pip3 install -r requirements.txt",
                    "pip3 install -r requirements-dev.txt",
                    "ACCOUNT=$(aws sts get-caller-identity | jq -r .Account)"
                ],
                commands=[
                    "cdk synth -c account=$ACCOUNT -c environmentType=$ENV_TYPE"
                ],
            )
        )

        quality_steps = self.create_code_quality_steps()
        pipeline.add_stage(
            DeployStage(
                scope=self,
                construct_id='QA',
                environment_type="qa"
            ),
            pre=quality_steps
        )

    def create_code_quality_steps(self):
        steps = []

        install_steps = [
            "npm install -g aws-cdk",
            "python3 -m venv .env",
            "chmod +x .env/bin/activate",
            ". .env/bin/activate",
            "pip3 install -r requirements.txt",
            "pip3 install -r requirements-dev.txt"
        ]

        environment = BuildEnvironment(
            build_image=LinuxBuildImage.STANDARD_7_0,
            compute_type=ComputeType.SMALL,
            privileged=True
        )

        steps.append(
            CodeBuildStep(
                "GitSecrets",
                input=self.source_stage,
                build_environment=environment,
                project_name="cdk-pipelines-git-secrets",
                install_commands=[
                    "SECRETS_FOLDER=git-secrets",
                    "mkdir $SECRETS_FOLDER",
                    "git clone --quiet https://github.com/awslabs/git-secrets.git $SECRETS_FOLDER",
                    "cd $SECRETS_FOLDER",
                    "make install",
                    "cd .. && rm -rf $SECRETS_FOLDER"
                ],
                commands=[
                    "git secrets --register-aws",
                    "git secrets --scan",
                    "echo No vulnerabilities detected. Have a really nice day!"
                ]
            )
        )

        steps.append(
            CodeBuildStep(
                "Linter",
                input=self.source_stage,
                build_environment=environment,
                project_name="cdk-pipelines-linter",
                install_commands=install_steps,
                commands=[
                    "python3 -m pylint cdk_workshop",
                    "python3 -m pylint tests",
                    "python3 -m pylint app.py"
                ]
            )
        )

        steps.append(
            CodeBuildStep(
                "UnitTests",
                input=self.source_stage,
                build_environment=environment,
                project_name="cdk-pipelines-unit-tests",
                install_commands=install_steps,
                commands=["python3 -m pytest"]
            )
        )

        steps.append(
            CodeBuildStep(
                "CfnNag",
                input=self.source_stage,
                build_environment=environment,
                project_name="cdk-pipelines-cfn-nag",
                install_commands=install_steps + ["gem install cfn-nag"],
                commands=[
                    "ACCOUNT=$(aws sts get-caller-identity | jq -r '.Account')",
                    "STACK_NAME=cdk-pipeline-scan",
                    "cdk synth $STACK_NAME -c account=$ACCOUNT -c environmentType=$ENV_TYPE > template.yaml",
                    "cfn_nag_scan --input-path template.yaml"
                ]
            )
        )

        steps.append(
            CodeBuildStep(
                "DependencyAudit",
                input=self.source_stage,
                build_environment=environment,
                project_name="cdk-pipelines-audit",
                install_commands=install_steps,
                commands=[
                    "safety check -r requirements.txt",
                    "safety check -r requirements-dev.txt"
                ]
            )
        )

        return steps
