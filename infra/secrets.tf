# JWT signing key for the backend. Generated once, kept in Terraform state,
# and reused on every deploy, so it stays the same between deploys.
resource "random_password" "secret_key" {
  length  = 64
  special = false
}