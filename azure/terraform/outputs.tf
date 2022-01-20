output "node-public" {
  value = [
    for instance in azurerm_linux_virtual_machine.couchbase_nodes:
    instance.public_ip_address
  ]
}

output "node-private" {
  value = [
    for instance in azurerm_linux_virtual_machine.couchbase_nodes:
    instance.private_ip_address
  ]
}
