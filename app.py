#!/usr/bin/env python3
from aws_cdk import App, Environment
from cdk_workshop.cdk_workshop_stack import CdkWorkshopStack

app = App()

environment_type = app.node.try_get_context("environmentType")
environment_context = app.node.try_get_context(environment_type)
region = environment_context["region"]
account = app.node.try_get_context("account")
tags = environment_context["tags"]
stack_name = f'{app.node.try_get_context("prefix")}-{environment_type}'

CdkWorkshopStack(
    app,
    stack_name,
     env = Environment(
        account = account,
        region = region
    ),
    tags=tags,
)

app.synth()
