output "hostnames" {
  value = [
    for instance in vsphere_virtual_machine.couchbase_nodes:
    "${instance.name}.${var.domain_name}"
  ]
}

output "addresses" {
  value = [
    for instance in vsphere_virtual_machine.couchbase_nodes:
    instance.default_ip_address
  ]
}
