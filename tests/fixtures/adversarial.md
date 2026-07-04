# Adversarial Markdown Fixture

This fixture exercises every element the AST must handle correctly.
All four generators produce output from this same source.

## 1. Nested Lists (3 levels)

- Level 1
  - Level 2
    - Level 3
- Back to level 1

1. First ordered
2. Second ordered
   1. Nested ordered
   2. Another nested
3. Back

## 2. Table with multi-line cell and list inside

| Feature | Details |
|---------|---------|
| Name | Alice |
| Hobbies | Reading, coding |
| Notes | - Loves Python\n- Also writes docs |

## 3. Code block with triple-backticks-looking content

```python
# This code block has a ``` inside a comment
def greet(name):
    return f"Hello, {name}!"
```

## 4. Bold, italic, inline-code combined

This is **bold**, *italic*, ***bold+italic***, and `inline code` all on one line.

## 5. Image with alt text

![TCET Campus Map](https://example.com/campus-map.png)

## 6. Blockquote containing a list

> Key takeaways:
> - First takeaway with **emphasis**
> - Second takeaway
> - Third takeaway

## 7. Horizontal rule

---

## 8. Links

This is a [link to TCET](https://tcet.com) and a [reference-style][ref] link.

[ref]: https://example.com
