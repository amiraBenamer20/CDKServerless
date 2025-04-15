#!/usr/bin/env python3
from aws_cdk import App, Environment
from cdk_workshop.pipeline_stack import PipelineStack

app = App()

environment_type = app.node.try_get_context("environmentType")
if not environment_type:
    environment_type = "qa"

environment_context = app.node.try_get_context(environment_type)
region = environment_context["region"]
account = app.node.try_get_context("account")

if account and region:
    environment = Environment(
         account = account,
         region = region
    )
else:
    environment = None


PipelineStack(
    app,
    "cdk-workshop-cdk-pipeline-stack",
    env = environment
)

app.synth()
