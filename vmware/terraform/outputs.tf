output "node-hostname" {
  value = [
    for instance in vsphere_virtual_machine.couchbase_nodes:
    "${instance.name}.${var.domain_name}"
  ]
}

output "node-private" {
  value = [
    for instance in vsphere_virtual_machine.couchbase_nodes:
    instance.default_ip_address
  ]
}
