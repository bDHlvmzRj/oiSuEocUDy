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
    }
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

  name        = each.key
  description = "Web ACL for ${each.key}"
  scope       = "REGIONAL"  # "CLOUDFRONT" を使用する場合は変更

  dynamic "default_action" {
    for_each = each.value.default_action == "ALLOW" ? [1] : [0]  # default_actionが "ALLOW" の場合
    content {
      allow {}  # allowの場合
    }
  }

  dynamic "default_action" {
    for_each = each.value.default_action == "BLOCK" ? [1] : [0]  # default_actionが "BLOCK" の場合
    content {
      block {}  # blockの場合
    }
  }

  dynamic "rule" {
    for_each = each.value.rules
    content {
      name     = rule.value.name
      priority = rule.value.priority

      dynamic "action" {
        for_each = rule.value.action == "ALLOW" ? [1] : [0]
        content {
          allow {}  # "ALLOW" の場合
        }
      }

      dynamic "action" {
        for_each = rule.value.action == "BLOCK" ? [1] : [0]
        content {
          block {}  # "BLOCK" の場合
        }
      }

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

          # 他のstatementタイプがある場合は以下に追加
          # dynamic "other_statement_type" { ... }
        }
      }
    }
  }
}
