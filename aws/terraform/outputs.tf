output "node-public" {
  value = [
    for instance in aws_instance.couchbase_nodes:
    instance.public_ip
  ]
}

output "node-private" {
  value = [
    for instance in aws_instance.couchbase_nodes:
    instance.private_ip
  ]
}
