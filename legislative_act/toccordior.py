from lxml import etree as et
from functools import lru_cache

from . import model as doc


SEPARATOR = " " + chr(8212) + " "


def _node_to_element_html(node: doc.ContentsTableNode) -> et.ElementBase:
    try:
        display_text = SEPARATOR.join((node.heading.ordinate, node.heading.title))
    except (AttributeError, TypeError):
        display_text = node.heading.ordinate
    li = et.Element("li", {"id": node.locator})
    a = et.SubElement(li, "a")
    a.attrib["href"] = node.href
    if node.children:
        # TODO: change this to
        #  https://stackoverflow.com/questions/10768451/inline-svg-in-css
        et.SubElement(
            a,
            "img",
            attrib={
                "class": "lex-fold-icon",
                "src": "/static/icons/minus-square-o.svg",
                "alt": "toggle",
            },
        ).tail = display_text
        li.attrib["class"] = "toc-node"
        ul = et.SubElement(li, "ul", {"class": "w3-ul"})
        for child in node.children:
            ul.append(_node_to_element_html(child))
    else:
        a.text = display_text
        li.attrib["class"] = "toc-leaf"
    return li


def _node_to_element_xml(node: doc.ContentsTableNode) -> et.ElementBase:
    if node.children:
        e = et.Element("Container")
    else:
        e = et.Element("Leaf")
    e.attrib["Name"] = node.heading.ordinate
    if getattr(node.heading, "title", None) is not None:
        e.attrib["Title"] = node.heading.title
    if node.href != "#":
        e.attrib["URL"] = node.href
    else:
        e.attrib["URL"] = node.locator
    for child in node.children:
        e.append(_node_to_element_xml(child))
    return e


def node_to_element(node: doc.ContentsTableNode, method="html"):
    if method == "html":
        return _node_to_element_html(node)
    assert method == "xml"
    return _node_to_element_xml(node)


class ContentsTable(doc.ContentsTable):
    def __hash__(self):
        return id(self)

    def embed(self, document_domain, document_id, version):
        href_template = f"/{document_domain}/{document_id}/{{}}/{version}"
        for node in self.table:
            if not node.children:
                href = href_template.format(node.locator)
            else:
                href = "#"
            node.href = href

    @property
    @lru_cache()
    def leaf_to_neighbour(self) -> dict:
        # TODO: Unittest this method: Edge-case: only a single leaf
        def node_2_neighbour(n: doc.ContentsTableNode):
            return {"ordinate": n.heading.ordinate, "id": n.locator}

        leaf_to_node = [node for node in self.table if len(node.children) == 0]
        result = {
            leaf_to_node[0].locator: {
                "left": None,
                "right": node_2_neighbour(leaf_to_node[1]),
            },
            leaf_to_node[-1].locator: {
                "left": node_2_neighbour(leaf_to_node[-2]),
                "right": None,
            },
        }
        result.update(
            {
                node.locator: {
                    "left": node_2_neighbour(leaf_to_node[k - 1]),
                    "right": node_2_neighbour(leaf_to_node[k + 1]),
                }
                for k, node in enumerate(leaf_to_node)
                if 0 < k < len(leaf_to_node) - 1
            }
        )
        return result

    def toccordior(self, version, document_id=None, method="html") -> et.ElementBase:
        version = version if version != "latest" else ""
        document_id = document_id or self.abstract.id_local
        self.embed(self.abstract.domain, document_id, version)
        if method == "html":
            toccordion = et.Element(
                "ul", {"id": "toccordion", "class": "w3-ul w3-medium"}
            )
        else:
            assert method == "xml"
            toccordion = et.Element("TableOfContents")
        for ultimate_parent in self.ultimate_parents():
            toccordion.append(node_to_element(ultimate_parent, method))
        return toccordion

    def locator_to_node(self):
        return {node.locator: node for node in self.table}

    def ultimate_parents(self):
        """Note: side-effect: nesting!!"""
        l2n = self.locator_to_node()
        for node in self.table:
            if len(node.children) == 0:
                continue
            if type(node.children[0]) == doc.ContentsTableNode:
                # self is already nested.
                for child in node.children:
                    del l2n[child.locator]
            elif type(node.children[0]) is str:
                node.children = [l2n.pop(locator) for locator in node.children]
        # list with only ultimate parents and children are
        # ContentsTableNode instances
        return l2n.values()
