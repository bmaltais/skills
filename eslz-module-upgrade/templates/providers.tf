terraform {
  required_version = ">= 1.9"
  required_providers {
    # Replace __PROVIDER_NAME__ with the actual provider (azurerm, azuread, azurestack, etc.)
    # Replace __PROVIDER_MAJOR__ with the target major version number (e.g. 4)
    # Add additional providers if the module uses more than one (check .terraform.lock.hcl)
    __PROVIDER_NAME__ = {
      source  = "hashicorp/__PROVIDER_NAME__"
      version = "~> __PROVIDER_MAJOR__.0"
    }
  }
}
