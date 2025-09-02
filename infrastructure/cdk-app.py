#!/usr/bin/env python3
import os
import aws_cdk as cdk
from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_lambda as _lambda,
    aws_dynamodb as dynamodb,
    aws_sqs as sqs,
    aws_sns as sns,
    aws_iam as iam,
    aws_logs as logs,
    aws_lambda_event_sources as lambda_event_sources,
    Duration
)
from constructs import Construct

class ECommerceOrderProcessingStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB Table for Orders
        orders_table = dynamodb.Table(
            self, "OrdersTable",
            table_name="ecommerce-orders",
            partition_key=dynamodb.Attribute(name="orderId", type=dynamodb.AttributeType.STRING),
            sort_key=dynamodb.Attribute(name="timestamp", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
            removal_policy=cdk.RemovalPolicy.DESTROY,
            encryption=dynamodb.TableEncryption.AWS_MANAGED
        )
        
        # Add Global Secondary Indexes
        orders_table.add_global_secondary_index(
            index_name="CustomerIdIndex",
            partition_key=dynamodb.Attribute(name="customerId", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )
        
        orders_table.add_global_secondary_index(
            index_name="StatusIndex",
            partition_key=dynamodb.Attribute(name="status", type=dynamodb.AttributeType.STRING),
            projection_type=dynamodb.ProjectionType.ALL
        )

        # SQS Queue for Order Processing
        order_processing_dlq = sqs.Queue(
            self, "OrderProcessingDLQ",
            queue_name="order-processing-dlq",
            encryption=sqs.QueueEncryption.KMS_MANAGED
        )

        order_processing_queue = sqs.Queue(
            self, "OrderProcessingQueue",
            queue_name="order-processing-queue",
            visibility_timeout=Duration.seconds(300),
            dead_letter_queue=sqs.DeadLetterQueue(
                max_receive_count=3,
                queue=order_processing_dlq
            ),
            encryption=sqs.QueueEncryption.KMS_MANAGED
        )

        # IAM Role for Lambda Functions
        lambda_execution_role = iam.Role(
            self, "LambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaBasicExecutionRole"),
                iam.ManagedPolicy.from_aws_managed_policy_name("service-role/AWSLambdaVPCAccessExecutionRole")
            ]
        )

        # Grant permissions to Lambda role
        orders_table.grant_read_write_data(lambda_execution_role)
        order_processing_queue.grant_send_messages(lambda_execution_role)
        order_processing_queue.grant_consume_messages(lambda_execution_role)

        # Lambda Function for Order Ingestion
        order_ingestion_function = _lambda.Function(
            self, "OrderIngestionFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/order_ingestion"),
            handler="index.handler",
            role=lambda_execution_role,
            timeout=Duration.seconds(30),
            environment={
                "ORDERS_TABLE_NAME": orders_table.table_name,
                "ORDER_QUEUE_URL": order_processing_queue.queue_url
            },
            log_group=logs.LogGroup(
                self, "OrderIngestionLogGroup",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=cdk.RemovalPolicy.DESTROY
            )
        )

        # Lambda Function for Order Processing
        order_processing_function = _lambda.Function(
            self, "OrderProcessingFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/order_processing"),
            handler="index.handler",
            role=lambda_execution_role,
            timeout=Duration.seconds(300),
            environment={
                "ORDERS_TABLE_NAME": orders_table.table_name
            },
            log_group=logs.LogGroup(
                self, "OrderProcessingLogGroup",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=cdk.RemovalPolicy.DESTROY
            )
        )

        # SQS Event Source for Order Processing Lambda
        order_processing_function.add_event_source(
            lambda_event_sources.SqsEventSource(order_processing_queue, batch_size=10)
        )

        # Lambda Function for Order Status Chatbot
        chatbot_function = _lambda.Function(
            self, "ChatbotFunction",
            runtime=_lambda.Runtime.PYTHON_3_9,
            code=_lambda.Code.from_asset("lambda/chatbot"),
            handler="index.handler",
            role=lambda_execution_role,
            timeout=Duration.seconds(30),
            environment={
                "ORDERS_TABLE_NAME": orders_table.table_name,
                "BEDROCK_MODEL_ID": "anthropic.claude-v2"
            },
            log_group=logs.LogGroup(
                self, "ChatbotLogGroup",
                retention=logs.RetentionDays.ONE_WEEK,
                removal_policy=cdk.RemovalPolicy.DESTROY
            )
        )

        # Grant Bedrock permissions to chatbot Lambda
        chatbot_function.add_to_role_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:InvokeModelWithResponseStream"
                ],
                resources=["*"]
            )
        )

        # API Gateway
        api = apigateway.RestApi(
            self, "ECommerceOrderAPI",
            rest_api_name="ecommerce-order-api",
            description="API for eCommerce order processing system",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=["Content-Type", "X-Amz-Date", "Authorization", "X-Api-Key"]
            ),
            deploy_options=apigateway.StageOptions(
                stage_name="prod",
                throttling_rate_limit=1000,
                throttling_burst_limit=2000,
                logging_level=apigateway.MethodLoggingLevel.INFO,
                data_trace_enabled=True,
                metrics_enabled=True
            )
        )

        # API Gateway Resources and Methods
        orders_resource = api.root.add_resource("orders")
        
        # POST /orders - Submit new order
        orders_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(order_ingestion_function),
            api_key_required=True
        )

        # GET /orders/{orderId} - Get order status
        order_resource = orders_resource.add_resource("{orderId}")
        order_resource.add_method(
            "GET",
            apigateway.LambdaIntegration(order_ingestion_function),
            api_key_required=True
        )

        # Chatbot resource
        chatbot_resource = api.root.add_resource("chatbot")
        chatbot_resource.add_method(
            "POST",
            apigateway.LambdaIntegration(chatbot_function),
            api_key_required=True
        )

        # API Key and Usage Plan
        api_key = api.add_api_key("ECommerceAPIKey")
        usage_plan = api.add_usage_plan(
            "ECommerceUsagePlan",
            name="ecommerce-usage-plan",
            throttle=apigateway.ThrottleSettings(
                rate_limit=100,
                burst_limit=200
            ),
            quota=apigateway.QuotaSettings(
                limit=10000,
                period=apigateway.Period.DAY
            )
        )
        usage_plan.add_api_key(api_key)
        usage_plan.add_api_stage(stage=api.deployment_stage)

        # SNS Topic for SMS notifications
        sms_notifications_topic = sns.Topic(
            self, "SMSNotificationsTopic",
            topic_name="ecommerce-order-notifications",
            display_name="eCommerce Order SMS Notifications"
        )

        # SNS SMS subscription for the phone number
        sns.Subscription(
            self, "SMSSubscription",
            topic=sms_notifications_topic,
            endpoint="+31629408162",  # Your phone number
            protocol=sns.SubscriptionProtocol.SMS
        )

        # Grant SNS permissions to Lambda execution role
        sms_notifications_topic.grant_publish(lambda_execution_role)

        # Update Lambda environment variables to include SNS topic ARN
        order_ingestion_function.add_environment("SNS_TOPIC_ARN", sms_notifications_topic.topic_arn)
        order_processing_function.add_environment("SNS_TOPIC_ARN", sms_notifications_topic.topic_arn)

        # CloudFormation Outputs
        cdk.CfnOutput(self, "APIEndpoint", value=api.url)
        cdk.CfnOutput(self, "OrdersTableName", value=orders_table.table_name)
        cdk.CfnOutput(self, "OrderQueueURL", value=order_processing_queue.queue_url)
        cdk.CfnOutput(self, "SNSTopicARN", value=sms_notifications_topic.topic_arn)

app = cdk.App()
ECommerceOrderProcessingStack(app, "ECommerceOrderProcessingStack")
app.synth()