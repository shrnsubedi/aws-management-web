from flask import Flask, render_template, request, jsonify, flash
import boto3
from datetime import datetime, timedelta, timezone
import os

app = Flask(__name__)
app.secret_key = os.env("SECRET-KEY")


@app.route('/')
def index():
    return render_template('index.html')

# EC2 ========

# Helper Functions ->

def list_regions():
    ec2 = boto3.client('ec2')
    return [region['RegionName'] +" : " + region["Endpoint"] for region in ec2.describe_regions()['Regions']]

def create_instance(region, keypair_name, security_group, instance_type, image_id):
    ec2 = boto3.resource('ec2', region_name=region)
    instance = ec2.create_instances(
        ImageId=image_id,
        MinCount=1,
        MaxCount=1,
        InstanceType=instance_type,
        KeyName=keypair_name,
        SecurityGroupIds=[security_group]
    )[0]
    instance.wait_until_running()
    instance.load()
    return instance.id

def get_all_instances(region):
    ec2 = boto3.client('ec2', region_name=region)
    instances = ec2.describe_instances()
    all_instances = []
    for reservation in instances['Reservations']:
        for instance in reservation['Instances']:
            all_instances.append({
                'InstanceId': instance['InstanceId'],
                'State': instance['State']['Name'],
            })
    return all_instances

def stop_instance(region, instance_id):
    ec2 = boto3.client('ec2', region_name=region)
    ec2.stop_instances(InstanceIds=[instance_id])

def get_instance_metrics(region, instance_id):
    cloudwatch = boto3.client('cloudwatch', region_name=region)
    metrics = [
        'CPUUtilization', 'DiskReadOps', 'DiskWriteOps', 'NetworkIn', 'NetworkOut', 'DiskReadBytes', 'DiskWriteBytes',
    ]

    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(days=1)
    metrics_data = {}

    for metric_name in metrics:
        response = cloudwatch.get_metric_statistics(
            Namespace='AWS/EC2',
            MetricName=metric_name,
            Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
            StartTime=start_time,
            EndTime=end_time,
            Period=300,
            Statistics=['Average']
        )
        if 'Datapoints' in response and response['Datapoints']:
            sorted_data = sorted(response['Datapoints'], key=lambda x: x['Timestamp'])
            metrics_data[metric_name] = [
                {'Timestamp': dp['Timestamp'], 'Average': dp['Average']} for dp in sorted_data
            ]
        else:
            metrics_data[metric_name] = []
    return metrics_data

# Routes

@app.route('/ec2')
def ec2_index():
    regions = list_regions()
    return render_template('ec2_index.html', regions=regions)

@app.route('/create_instance', methods=['POST'])
def create_instance_route():
    data = request.json
    region = data['region']
    keypair_name = data['keypair_name']
    security_group = data['security_group']
    instance_type = data['instance_type']
    image_id = data['image_id']

    instance_id = create_instance(region, keypair_name, security_group, instance_type, image_id)
    return jsonify({'instance_id': instance_id})

@app.route('/instances', methods=['POST'])
def instances():
    region = request.json['region']
    instances = get_all_instances(region)
    return jsonify({'instances': instances})

@app.route('/stop_instance', methods=['POST'])
def stop_instance():
    data = request.get_json()
    region = data.get('region')
    instance_id = data.get('instance_id')
    try:
        ec2 = boto3.client('ec2', region_name=region)
        ec2.stop_instances(InstanceIds=[instance_id])
        return jsonify({'message': f'Instance {instance_id} is stopping.'})
    except Exception as e:
        return jsonify({'message': str(e)}), 400

@app.route('/metrics', methods=['POST'])
def metrics():
    data = request.get_json()
    region = data.get('region')
    instance_id = data.get('instance_id')
    metrics_data = get_instance_metrics(region, instance_id)
    return jsonify({'metrics': metrics_data})

# S3 ========

# Helper Functions -> 

def create_bucket_in_regions(bucket_name, regions):
    s3 = boto3.client('s3')
    results = {}
    for region in regions:
        try:
            if region == "us-east-1":
                s3.create_bucket(Bucket=bucket_name)
            else:
                s3.create_bucket(Bucket=bucket_name, CreateBucketConfiguration={'LocationConstraint': region})
            results[region] = "Created successfully"
        except Exception as e:
            results[region] = str(e)
    return results

def list_buckets():
    s3 = boto3.client('s3')
    try:
        buckets = s3.list_buckets()
        return [bucket['Name'] for bucket in buckets['Buckets']]
    except Exception as e:
        return str(e)

def upload_object(bucket_name, object_name, content):
    s3 = boto3.client('s3')
    try:
        s3.put_object(Bucket=bucket_name, Key=object_name, Body=content)
        return f"Object '{object_name}' uploaded to bucket '{bucket_name}' successfully."
    except Exception as e:
        return str(e)

def delete_object(bucket_name, object_name):
    s3 = boto3.client('s3')
    try:
        s3.delete_object(Bucket=bucket_name, Key=object_name)
        return f"Object '{object_name}' deleted from bucket '{bucket_name}' successfully."
    except Exception as e:
        return str(e)

def list_objects(bucket_name):
    s3 = boto3.client('s3')
    try:
        objects = s3.list_objects_v2(Bucket=bucket_name)
        items = [
            {"Key": obj["Key"], "Size": obj["Size"]} for obj in objects.get("Contents", [])
        ]
        return jsonify({"objects": items})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
# Endpoints
    
@app.route('/s3')
def s3_index():
    regions = list_regions()
    return render_template('s3_index.html', regions=regions)

@app.route('/list_buckets', methods=['GET'])
def list_buckets_route():
    try:
        buckets = list_buckets()
        return jsonify({'buckets': buckets})
    except Exception as e:
        return jsonify({'error': str(e)}), 400
       
@app.route('/list_objects', methods=['GET'])
def list_objects_route():
    bucket_name = request.args.get('bucket_name')
    results =  list_objects(bucket_name)
    return results

@app.route('/create_bucket', methods=['POST'])
def create_bucket():
    data = request.json
    bucket_name = data.get('bucket_name')
    region = data.get('region')
    s3 = boto3.client('s3', region_name = region)
    try:
        s3.create_bucket(Bucket=bucket_name,
                CreateBucketConfiguration={
                'LocationConstraint': region
        })
        return jsonify({'message': f'Bucket {bucket_name} created successfully'})
    except Exception as e:
        print(e)
        return jsonify({'error': str(e)}), 400


@app.route('/upload_object', methods=['POST'])
def upload_object_route():
    bucket_name = request.form['bucket_name']
    print(bucket_name)
    object_name = request.form['object_name']
    file = request.files['file']
    s3 = boto3.client('s3')

    try:
        s3.upload_fileobj(file, bucket_name, object_name)
        return jsonify({'message': 'Object uploaded successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 400


@app.route('/delete_object', methods=['POST'])
def delete_from_bucket():
    data = request.json
    bucket_name = data['bucket_name']
    object_name = data['object_name']
    result = delete_object(bucket_name, object_name)
    return jsonify({'message': result})

if __name__ == "__main__":
    app.run(debug=True)