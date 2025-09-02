import json
import boto3
import os
import logging
import time
import random
from datetime import datetime
from decimal import Decimal

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')
cloudwatch = boto3.client('cloudwatch')
sns = boto3.client('sns')

# Environment variables
ORDERS_TABLE_NAME = os.environ['ORDERS_TABLE_NAME']
SNS_TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

def handler(event, context):
    """
    Lambda function to process orders from SQS queue
    """
    processed_orders = []
    failed_orders = []
    
    try:
        # Process each SQS record
        for record in event['Records']:
            try:
                # Parse message body
                message_body = json.loads(record['body'])
                order_id = message_body['orderId']
                action = message_body['action']
                
                logger.info(f"Processing order {order_id} with action {action}")
                
                if action == 'PROCESS_ORDER':
                    result = process_order(order_id)
                    if result:
                        processed_orders.append(order_id)
                    else:
                        failed_orders.append(order_id)
                else:
                    logger.warning(f"Unknown action: {action}")
                    failed_orders.append(order_id)
                    
            except Exception as e:
                logger.error(f"Error processing SQS record: {str(e)}")
                failed_orders.append(record.get('messageId', 'unknown'))
        
        # Send metrics to CloudWatch
        send_processing_metrics(len(processed_orders), len(failed_orders))
        
        logger.info(f"Batch processing complete. Success: {len(processed_orders)}, Failed: {len(failed_orders)}")
        
        return {
            'statusCode': 200,
            'processedOrders': processed_orders,
            'failedOrders': failed_orders
        }
        
    except Exception as e:
        logger.error(f"Error in order processing handler: {str(e)}")
        return {
            'statusCode': 500,
            'error': str(e)
        }

def process_order(order_id):
    """
    Process a single order through business logic
    """
    try:
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        
        # Get order details
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('orderId').eq(order_id)
        )
        
        if not response['Items']:
            logger.error(f"Order {order_id} not found")
            return False
        
        order = response['Items'][0]
        current_status = order.get('status', 'PENDING')
        
        # Only process pending orders
        if current_status != 'PENDING':
            logger.info(f"Order {order_id} already processed (status: {current_status})")
            return True
        
        # Simulate order processing steps
        processing_steps = [
            ('VALIDATING', validate_order),
            ('INVENTORY_CHECK', check_inventory),
            ('PAYMENT_PROCESSING', process_payment),
            ('FULFILLMENT', fulfill_order)
        ]
        
        for status, processing_function in processing_steps:
            logger.info(f"Order {order_id}: {status}")
            
            # Update order status
            update_order_status(order_id, status, order['timestamp'])
            
            # Execute processing step
            success = processing_function(order)
            
            if not success:
                logger.error(f"Order {order_id} failed at step {status}")
                update_order_status(order_id, 'FAILED', order['timestamp'], f"Failed at {status}")
                # Send failure notification
                send_order_notification(order_id, 'FAILED', order, f"Failed at {status}")
                return False
            
            # Simulate processing time
            time.sleep(0.1)
        
        # Mark order as completed
        update_order_status(order_id, 'COMPLETED', order['timestamp'])
        logger.info(f"Order {order_id} completed successfully")
        
        # Send completion notification
        send_order_notification(order_id, 'COMPLETED', order)
        
        return True
        
    except Exception as e:
        logger.error(f"Error processing order {order_id}: {str(e)}")
        update_order_status(order_id, 'FAILED', order.get('timestamp', ''), str(e))
        return False

def update_order_status(order_id, status, timestamp, error_message=None):
    """
    Update order status in DynamoDB
    """
    try:
        table = dynamodb.Table(ORDERS_TABLE_NAME)
        
        update_expression = "SET #status = :status, updatedAt = :updated_at"
        expression_attribute_names = {"#status": "status"}
        expression_attribute_values = {
            ":status": status,
            ":updated_at": datetime.utcnow().isoformat()
        }
        
        if error_message:
            update_expression += ", errorMessage = :error_message"
            expression_attribute_values[":error_message"] = error_message
        
        table.update_item(
            Key={
                'orderId': order_id,
                'timestamp': timestamp
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )
        
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")

def validate_order(order):
    """
    Validate order data and business rules
    """
    try:
        # Check required fields
        required_fields = ['customerId', 'items', 'totalAmount']
        for field in required_fields:
            if field not in order or not order[field]:
                logger.error(f"Validation failed: missing {field}")
                return False
        
        # Validate items
        if not isinstance(order['items'], list) or len(order['items']) == 0:
            logger.error("Validation failed: no items in order")
            return False
        
        # Validate total amount
        if float(order['totalAmount']) <= 0:
            logger.error("Validation failed: invalid total amount")
            return False
        
        logger.info(f"Order {order['orderId']} validation successful")
        return True
        
    except Exception as e:
        logger.error(f"Validation error: {str(e)}")
        return False

def check_inventory(order):
    """
    Check inventory availability for order items
    """
    try:
        # Simulate inventory check
        for item in order['items']:
            # Simulate occasional inventory shortage (10% chance)
            if random.random() < 0.1:
                logger.warning(f"Inventory shortage for item {item.get('productId', 'unknown')}")
                return False
        
        logger.info(f"Order {order['orderId']} inventory check successful")
        return True
        
    except Exception as e:
        logger.error(f"Inventory check error: {str(e)}")
        return False

def process_payment(order):
    """
    Process payment for the order
    """
    try:
        # Simulate payment processing
        total_amount = float(order['totalAmount'])
        
        # Simulate payment failure (5% chance)
        if random.random() < 0.05:
            logger.error(f"Payment processing failed for order {order['orderId']}")
            return False
        
        # Simulate processing time based on amount
        processing_time = min(0.5, total_amount / 1000)
        time.sleep(processing_time)
        
        logger.info(f"Order {order['orderId']} payment processed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Payment processing error: {str(e)}")
        return False

def fulfill_order(order):
    """
    Fulfill the order (prepare for shipping)
    """
    try:
        # Simulate fulfillment process
        item_count = len(order['items'])
        
        # Simulate fulfillment time based on item count
        fulfillment_time = min(1.0, item_count * 0.1)
        time.sleep(fulfillment_time)
        
        logger.info(f"Order {order['orderId']} fulfilled successfully")
        return True
        
    except Exception as e:
        logger.error(f"Fulfillment error: {str(e)}")
        return False

def send_processing_metrics(successful_orders, failed_orders):
    """
    Send custom metrics to CloudWatch
    """
    try:
        # Send successful orders metric
        cloudwatch.put_metric_data(
            Namespace='ECommerce/OrderProcessing',
            MetricData=[
                {
                    'MetricName': 'SuccessfulOrders',
                    'Value': successful_orders,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                },
                {
                    'MetricName': 'FailedOrders',
                    'Value': failed_orders,
                    'Unit': 'Count',
                    'Timestamp': datetime.utcnow()
                }
            ]
        )
        
        logger.info(f"Metrics sent to CloudWatch: Success={successful_orders}, Failed={failed_orders}")
        
    except Exception as e:
        logger.error(f"Error sending metrics to CloudWatch: {str(e)}")

def send_order_notification(order_id, event_type, order_data=None, error_message=None):
    """
    Send SMS notification for order events
    """
    if not SNS_TOPIC_ARN:
        logger.warning("SNS_TOPIC_ARN not configured, skipping SMS notification")
        return
    
    try:
        if event_type == 'COMPLETED':
            total_amount = order_data.get('totalAmount', 'Unknown')
            customer_id = order_data.get('customerId', 'Unknown')
            item_count = len(order_data.get('items', []))
            
            message = f"✅ Order Completed!\n"
            message += f"Order ID: {order_id[:8]}...\n"
            message += f"Customer: {customer_id}\n"
            message += f"Items: {item_count}\n"
            message += f"Total: €{total_amount}\n"
            message += f"Status: Ready for shipping\n"
            message += f"Completed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
        elif event_type == 'FAILED':
            customer_id = order_data.get('customerId', 'Unknown') if order_data else 'Unknown'
            
            message = f"❌ Order Failed!\n"
            message += f"Order ID: {order_id[:8]}...\n"
            message += f"Customer: {customer_id}\n"
            if error_message:
                message += f"Reason: {error_message}\n"
            message += f"Please contact customer service\n"
            message += f"Failed: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
            
        else:
            message = f"Order {order_id[:8]}... - {event_type}"
            if error_message:
                message += f" ({error_message})"
        
        # Send SMS via SNS
        response = sns.publish(
            TopicArn=SNS_TOPIC_ARN,
            Message=message,
            Subject=f"eCommerce Order {event_type}"
        )
        
        logger.info(f"SMS notification sent for order {order_id} - {event_type}")
        
    except Exception as e:
        logger.error(f"Failed to send SMS notification: {str(e)}")
        # Don't fail the main process if notification fails