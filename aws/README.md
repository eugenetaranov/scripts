ansible_bootstrap.py - executed upon instance startup to run ansible playbooks
dns_update.py - updates Route53 zone upon startup
dynamodb_clone.py - clones DynamoDB tables with defined prefix and copies defined number of records from original table
ec2inventory.py - ansible compatible AWS EC2 inventory
dynamodb_export.py - exports specified number of records from each DynamoDB table into separate CSV files along with headers
ec2_instances_report.py - prints out instance type, name, avg cpu usage for past 2 weeks
s3_compress_logs.py - compresses ELB access logs stored in S3
mongo_copy.py - restores mongo data from snapshot, attaches replicaset, reconfigures (prod->stage mongo migration)
eip_check.py - monitors and migrates elastic IP to the other tagged instance
