# resource "azurerm_resource_group" "webinar" {
#   name     = "gpu-webinar"
#   location = "westus"
# }

# resource "azurerm_virtual_network" "main" {
#   name                = "gpu-webinar-network"
#   address_space       = ["10.0.0.0/16"]
#   location            = azurerm_resource_group.webinar.location
#   resource_group_name = azurerm_resource_group.webinar.name
# }

# resource "azurerm_subnet" "internal" {
#   name                 = "gpu-webinar-internal"
#   resource_group_name  = azurerm_resource_group.webinar.name
#   virtual_network_name = azurerm_virtual_network.main.name
#   address_prefixes     = ["10.0.2.0/24"]
# }

# resource "azurerm_network_interface" "main" {
#   name                = "gpu-webinar-nic"
#   location            = azurerm_resource_group.webinar.location
#   resource_group_name = azurerm_resource_group.webinar.name

#   ip_configuration {
#     name                          = "testconfiguration1"
#     subnet_id                     = azurerm_subnet.internal.id
#     private_ip_address_allocation = "Dynamic"
#   }
# }

# module "ubuntu-tailscale-azure" {
#   source         = "lbrlabs/tailscale/cloudinit"
#   version        = "0.0.3"
#   auth_key       = var.tailscale_auth_key
#   enable_ssh     = true
#   hostname       = "openwebui-vm"
#   advertise_tags = ["tag:gpu"]
# }

# resource "azurerm_virtual_machine" "main" {
#   name                  = "openwebui-vm"
#   location              = azurerm_resource_group.webinar.location
#   resource_group_name   = azurerm_resource_group.webinar.name
#   network_interface_ids = [azurerm_network_interface.main.id]
#   vm_size               = "Standard_DS1_v2"
#   delete_os_disk_on_termination = true
#   delete_data_disks_on_termination = true
  
  

#   storage_image_reference {
#     publisher = "Canonical"
#     offer     = "0001-com-ubuntu-server-jammy"
#     sku       = "22_04-lts"
#     version   = "latest"
#   }
#   storage_os_disk {
#     name              = "os"
#     caching           = "ReadWrite"
#     create_option     = "FromImage"
#     managed_disk_type = "Standard_LRS"
#     disk_size_gb = 100
#   }
#   os_profile {
#     computer_name  = "openwebui"
#     admin_username = "lbriggs"
#     admin_password = "correct-h0rse-battery-stab!e"
#     custom_data = module.ubuntu-tailscale-azure.rendered
#   }

#   os_profile_linux_config {
#     disable_password_authentication = false
#   }

  

# }