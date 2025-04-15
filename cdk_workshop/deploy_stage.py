from aws_cdk import Stage, Environment
from constructs import Construct
from cdk_workshop.cdk_workshop_stack import CdkWorkshopStack

class DeployStage(Stage):

    def __init__(self, scope: Construct, construct_id: str, environment_type: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.node.set_context("environmentType",environment_type)
        environment_type = self.node.try_get_context("environmentType")
        self.context = self.node.try_get_context(environment_type)

        stack_name = self.node.try_get_context("prefix")

        self.stack = CdkWorkshopStack(
            self,
            stack_name,
             env = Environment(
                account = self.account,
                region = self.region
            )
        )
