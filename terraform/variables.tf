variable "tailscale_auth_key" {
  description = "Node authorization key; if it begins with 'file:', then it's a path to a file containing the authkey"
  type        = string
}

variable "tailscale_api_key" {
  description = "Tailscale API key"
  type        = string

}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "gcp_project" {
  description = "GCP project"
  type        = string
}

variable "gcp_region" {
  description = "GCP region"
  type        = string
  default     = "us-central1t"
}