import json
import boto3
import logging
import urllib3
import time

# initialize logger
LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

def lambda_handler(event, context):

    LOGGER.info("Event : %s" % (event))

    ## create exceptions list to catch exceptions messages
    exceptions = []
    exceptions.clear()

    ## Functions

    def errorResponse(code,msg):
        return {
            'statusCode': code,
            'headers':{
                'Access-Control-Allow-Origin':'*',
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,GET'
            },
            'body': json.dumps(msg)
        }


    ## Channel list
    def eml_list_channels(medialive_region):

        LOGGER.info("Scanning MediaLive channels in region: %s" % (medialive_region))

        # Initialize medialive boto3 client
        eml_client = boto3.client('medialive',region_name=medialive_region)

        try:
            response = eml_client.list_channels(MaxResults=123)

            msg = "MediaLive channel list response for region %s: %s " % (medialive_region,response)
            LOGGER.debug(msg)

        except Exception as e:

            msg = "Unable to perform list channels in region %s: %s" % (medialive_region,e)
            exceptions.append(msg)
            return msg

        return response

    def insert_scte(medialive_region,medialive_channel_id,ad_break_length):

        LOGGER.info("Attempting to insert SCTE35 message")

        # Initialize medialive boto3 client
        eml_client = boto3.client('medialive',region_name=medialive_region)

        action_name = "%s_splice_insert" % (str(int(time.time()))) #

        scte35_create_dict = dict()
        scte35_create_dict['ScheduleActions'] = []
        scte35_create_dict['ScheduleActions'].append({})
        scte35_create_dict['ScheduleActions'][0]['ActionName'] = action_name
        scte35_create_dict['ScheduleActions'][0]['ScheduleActionStartSettings'] = {}
        scte35_create_dict['ScheduleActions'][0]['ScheduleActionStartSettings']['ImmediateModeScheduleActionStartSettings'] = {}
        scte35_create_dict['ScheduleActions'][0]['ScheduleActionSettings'] = {}
        scte35_create_dict['ScheduleActions'][0]['ScheduleActionSettings']['Scte35SpliceInsertSettings'] = {}
        scte35_create_dict['ScheduleActions'][0]['ScheduleActionSettings']['Scte35SpliceInsertSettings']['Duration'] = ad_break_length * 90000
        scte35_create_dict['ScheduleActions'][0]['ScheduleActionSettings']['Scte35SpliceInsertSettings']['SpliceEventId'] = int(time.time())

        try:
            response = eml_client.batch_update_schedule(ChannelId=medialive_channel_id,Creates=scte35_create_dict)

            msg = "MediaLive channel SCTE35 injection successful!"
            LOGGER.debug(msg)

        except Exception as e:

            msg = "Unable to insert SCTE35, got exception: %s" % (e)
            exceptions.append(msg)

        return msg

    ## Channel schedule lookup and old action listing
    def describe_channel_schedule(medialive_channel_id,medialive_region):

        # Initialize medialive boto3 client
        eml_client = boto3.client('medialive',region_name=medialive_region)

        # Try block to get schedule from MediaLive channel
        try:

            msg = "Attempting to get schedule for channel %s in region %s" % (medialive_channel_id,medialive_region)

            response = eml_client.describe_schedule(ChannelId=medialive_channel_id,MaxResults=123)
            LOGGER.debug("Describe_Channel_Response: %s " % (response))

            schedule_actions = response['ScheduleActions']

        except Exception as e:
            msg = "Unable to get MediaLive schedule for channel %s in region %s: %s" % (medialive_channel_id,medialive_region,e)
            exceptions.append(msg)
            LOGGER.warning(msg)
            return False

        schedule_actions = response['ScheduleActions']

        if len(schedule_actions) == 0:
            return True

        safe_action = True
        for action in schedule_actions:


            if "splice_insert" in action['ActionName']:
                if (int(action['ActionName'].split("_")[0]) + (int(action['ScheduleActionSettings']['Scte35SpliceInsertSettings']['Duration']) / 90000)) > int(time.time()):
                    safe_action = False

        return safe_action


        return schedule_actions
        # get number of schedule actions in list
        # schedule_actions_length = len(schedule_actions)
        # LOGGER.info("Found %s schedule actions for channel %s in region %s" % (str(schedule_actions_length),medialive_channel_id,region))


    ## Functions

    event_path = event['path']

    if event_path == "/listChannels":

        LOGGER.info("API Call received for listChannels")

        ## Get region from API call
        try:
            aws_region = event['queryStringParameters']['region']
        except Exception as e:
            msg = "Unable to get region value from expected query string input"
            return errorResponse(500,msg)

        eml_list_channels_response = eml_list_channels(aws_region)

        eml_channels = eml_list_channels_response['Channels']

        eml_channels_list = []
        if len(eml_channels) == 0:
            return {
                'statusCode': 200,
                'headers':{
                    'Access-Control-Allow-Origin':'*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,GET'
                },
                'body': json.dumps(eml_channels_list)
            }

        else:
            for channel in eml_channels:
                eml_channels_list.append({"ChannelId":channel['Id'],"ChannelName":channel['Name']})

            return {
                'statusCode': 200,
                'body': json.dumps(eml_channels_list)
            }

    elif event_path == "/insertSCTE":

        LOGGER.info("API Call received for insertSCTE")

        ## Get region, channel id, and break duration from query strings
        try:
            medialive_region = event['queryStringParameters']['region']
            medialive_channel_id = event['queryStringParameters']['chid']
            ad_break_length = int(event['queryStringParameters']['duration'])
        except Exception as e:
            msg = "Unable to get region, medialive channel id, or duration from API call"
            return errorResponse(500,msg)


        if describe_channel_schedule(medialive_channel_id,medialive_region):

            insert_response = insert_scte(medialive_region,medialive_channel_id,ad_break_length)

            return {
                'statusCode': 200,
                'headers':{
                    'Access-Control-Allow-Origin':'*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,GET'
                },
                'body': json.dumps({"response":insert_response})
            }

        else:

            msg = "Unable to insert SCTE53, too close to existing event. Try again soon"

            return {
                'statusCode': 200,
                'headers':{
                    'Access-Control-Allow-Origin':'*',
                    'Access-Control-Allow-Headers': '*',
                    'Access-Control-Allow-Methods': 'OPTIONS,POST,PUT,GET'
                },
                'body': json.dumps({"response":msg})
            }


    elif "/ui" in event_path:

        ## Initialize S3 boto3 client
        s3 = boto3.client('s3')

        # Create urllib3 pool manager
        http = urllib3.PoolManager()

        # parse event for bucket and key
        try:
            bucket = event['pathParameters']['proxy'].split("/")[1]
            key =  '/'.join(event['pathParameters']['proxy'].split("/")[2:])
        except:
            body = "request url not well formed"
            base64encoded = False
            return api_response(500,headers,body,base64encoded)

        try:
            s3_response = s3.get_object(Bucket=bucket, Key=key)
            headers = s3_response['ResponseMetadata']['HTTPHeaders']
            if ".jpg" in key:
                body = base64.b64encode(s3_response['Body'].read()).decode('utf-8')
                base64encoded = True
            else:
                body = s3_response['Body'].read().decode('utf-8')
                base64encoded = False

            return {
                'statusCode': 200,
                'headers': headers,
                'body':body
            }

        except:
            msg = "cannot get ui files"
            return errorResponse(500,msg)

    else:

        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Headers': '*',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Methods': 'OPTIONS,PUT,POST,GET'
            }
        }

        # msg = "API path is not supported"
        # return errorResponse(500,msg)