# To-Dos and Ideas

## Templating

- Add a `metadata` jinja global (or some such) to provide access to document metadata.
  This could be used to template _judge name_, _trial date_, etc.


## Bugs in Other Packages

### types-lxml

- `lxml.etree.register_namespace` (and `register_namespaces`?) is missing.
- `lxml.etree.QName` is not equality-comparable to str | bytes.
