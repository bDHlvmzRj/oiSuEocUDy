resource "aws_wafv2_web_acl" "web_acl" {
  for_each = {
    "web_acl_1" = {
      default_action = "ALLOW"
      rules = [
        {
          name     = "rule1"
          priority = 1
          action   = "ALLOW"
          statement = [
            {
              byte_match_statement = {
                search_string = "GET"
                field_to_match = {
                  type = "METHOD"
                  data = "REQUEST_METHOD"
                }
              }
            }
          ]
        },
        {
          name     = "rule2"
          priority = 2
          action   = "BLOCK"
          statement = [
            {
              byte_match_statement = {
                search_string = "POST"
                field_to_match = {
                  type = "METHOD"
                  data = "REQUEST_METHOD"
                }
              }
            }
          ]
        }
      ]
    },
    "web_acl_2" = {
      default_action = "BLOCK"
      rules = [
        {
          name     = "rule1"
          priority = 1
          action   = "ALLOW"
          statement = [
            {
              byte_match_statement = {
                search_string = "GET"
                field_to_match = {
                  type = "METHOD"
                  data = "REQUEST_METHOD"
                }
              }
            }
          ]
        }
      ]
    }
  }

  # Web ACL name and description
  name        = each.key
  description = "Web ACL for ${each.key}"
  scope       = "REGIONAL"  # "CLOUDFRONT" for CloudFront usage

  # Dynamic block for default action: allow or block
  dynamic "default_action" {
    for_each = each.value.default_action == "ALLOW" ? [1] : [0]  # Default action "ALLOW"
    content {
      allow {}  # If default action is ALLOW
    }
  }

  dynamic "default_action" {
    for_each = each.value.default_action == "BLOCK" ? [1] : [0]  # Default action "BLOCK"
    content {
      block {}  # If default action is BLOCK
    }
  }

  # Dynamic block for rules
  dynamic "rule" {
    for_each = each.value.rules
    content {
      name     = rule.value.name
      priority = rule.value.priority

      # Dynamic block for action (ALLOW or BLOCK)
      dynamic "action" {
        for_each = rule.value.action == "ALLOW" ? [1] : [0]
        content {
          allow {}  # If rule action is ALLOW
        }
      }

      dynamic "action" {
        for_each = rule.value.action == "BLOCK" ? [1] : [0]
        content {
          block {}  # If rule action is BLOCK
        }
      }

      # Dynamic block for statements
      dynamic "statement" {
        for_each = rule.value.statement
        content {
          dynamic "byte_match_statement" {
            for_each = contains(keys(statement.value), "byte_match_statement") ? [1] : []
            content {
              search_string = statement.value.byte_match_statement.search_string
              field_to_match {
                type = statement.value.byte_match_statement.field_to_match.type
                data = statement.value.byte_match_statement.field_to_match.data
              }
            }
          }

          # Add more statement types as needed (e.g., ip_set_reference_statement, size_constraint_statement)
          dynamic "ip_set_reference_statement" {
            for_each = contains(keys(statement.value), "ip_set_reference_statement") ? [1] : []
            content {
              arn = statement.value.ip_set_reference_statement.arn
            }
          }

          dynamic "size_constraint_statement" {
            for_each = contains(keys(statement.value), "size_constraint_statement") ? [1] : []
            content {
              comparison_operator = statement.value.size_constraint_statement.comparison_operator
              size                = statement.value.size_constraint_statement.size
              field_to_match {
                type = statement.value.size_constraint_statement.field_to_match.type
                data = statement.value.size_constraint_statement.field_to_match.data
              }
            }
          }
        }
      }
    }
  }
}
