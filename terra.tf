resource "aws_wafv2_web_acl" "web_acl" {
  for_each = var.web_acls

  name        = each.key
  description = "Web ACL for ${each.key}"
  scope       = "REGIONAL"  # "CLOUDFRONT" を使用する場合は変更

  dynamic "default_action" {
    for_each = each.value.default_action == "ALLOW" ? [1] : [0]  # AllowまたはBlockで動的に切り替える
    content {
      allow {}  # allowの場合
    }
  }

  dynamic "default_action" {
    for_each = each.value.default_action == "BLOCK" ? [1] : [0]  # AllowまたはBlockで動的に切り替える
    content {
      block {}  # blockの場合
    }
  }

  dynamic "rule" {
    for_each = each.value.rules
    content {
      name     = rule.value.name
      priority = rule.value.priority

      action {
        allow {}  # "ALLOW" の場合
        block {}  # "BLOCK" の場合
      }

      statement {
        byte_match_statement {
          search_string = rule.value.statement.byte_match_statement.search_string
          field_to_match {
            type = rule.value.statement.byte_match_statement.field_to_match.type
            data = rule.value.statement.byte_match_statement.field_to_match.data
          }
        }
      }
    }
  }
}
