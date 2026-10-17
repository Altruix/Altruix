# Copyright (C) 2021-present by Altruix@Github, < https://github.com/Altruix >.
#
# This file is part of < https://github.com/Altruix/Altruix > project,
# and is released under the "GNU v3.0 License Agreement".
# Please see < https://github.com/Altriux/Altruix/blob/main/LICENSE >
#
# All rights reserved.

from __future__ import annotations

import re
import time
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("altruix.mongo_parser")


def _safe_eq(actual: Any, expected: Any) -> bool:
    """Check equality with flexible string/integer coercion for IDs."""
    if actual == expected:
        return True
    if isinstance(actual, (int, str)) and isinstance(expected, (int, str)):
        try:
            return int(actual) == int(expected)
        except (ValueError, TypeError):
            pass
    return False


def _get_nested(doc: Any, path: str) -> Any:
    """Retrieve value at nested dot path (e.g. 'user.id' or 'settings.flags.0')."""
    if not isinstance(doc, dict):
        return None
    if path in doc:
        return doc[path]
    if "." not in path:
        return doc.get(path)

    parts = path.split(".")
    curr = doc
    for p in parts:
        if isinstance(curr, dict):
            curr = curr.get(p)
        elif isinstance(curr, list) and p.isdigit():
            idx = int(p)
            curr = curr[idx] if 0 <= idx < len(curr) else None
        else:
            return None
    return curr


def _set_nested(doc: Dict[str, Any], path: str, value: Any) -> None:
    """Set value at nested dot path (e.g. 'user.id')."""
    if "." not in path:
        doc[path] = value
        return

    parts = path.split(".")
    curr = doc
    for p in parts[:-1]:
        if p not in curr or not isinstance(curr[p], dict):
            curr[p] = {}
        curr = curr[p]
    curr[parts[-1]] = value


def _unset_nested(doc: Dict[str, Any], path: str) -> None:
    """Remove value at nested dot path."""
    if "." not in path:
        doc.pop(path, None)
        return

    parts = path.split(".")
    curr = doc
    for p in parts[:-1]:
        if isinstance(curr, dict) and p in curr:
            curr = curr[p]
        else:
            return
    if isinstance(curr, dict):
        curr.pop(parts[-1], None)


class PyMongoInstructionParser:
    """
    Universal Parser and execution engine that translates PyMongo / Motor queries
    and update instructions for PostgreSQL, SQLite, and Redis backends.
    """

    @staticmethod
    def match_document(doc: Dict[str, Any], query: Dict[str, Any]) -> bool:
        """
        Evaluate if a dictionary document satisfies a MongoDB query filter.
        Supports:
        - Exact match & loose numeric match
        - Dot-notation paths ('a.b.c')
        - $eq, $ne, $gt, $gte, $lt, $lte
        - $in, $nin, $all, $size
        - $exists
        - $regex & $options (or compiled regex)
        - $or, $and, $nor, $not
        - $elemMatch
        """
        if not query:
            return True

        for key, expected in query.items():
            if key == "$or" and isinstance(expected, list):
                if not any(PyMongoInstructionParser.match_document(doc, subq) for subq in expected):
                    return False
                continue

            if key == "$and" and isinstance(expected, list):
                if not all(PyMongoInstructionParser.match_document(doc, subq) for subq in expected):
                    return False
                continue

            if key == "$nor" and isinstance(expected, list):
                if any(PyMongoInstructionParser.match_document(doc, subq) for subq in expected):
                    return False
                continue

            actual = _get_nested(doc, key)

            if isinstance(expected, dict):
                for op, val in expected.items():
                    if op == "$eq":
                        if not _safe_eq(actual, val):
                            return False
                    elif op == "$ne":
                        if _safe_eq(actual, val):
                            return False
                    elif op == "$in":
                        if not isinstance(val, (list, tuple, set)):
                            val = [val]
                        if isinstance(actual, (list, tuple, set)):
                            if not any(any(_safe_eq(a_item, v_item) for v_item in val) for a_item in actual):
                                return False
                        elif not any(_safe_eq(actual, item) for item in val):
                            return False
                    elif op == "$nin":
                        if not isinstance(val, (list, tuple, set)):
                            val = [val]
                        if isinstance(actual, (list, tuple, set)):
                            if any(any(_safe_eq(a_item, v_item) for v_item in val) for a_item in actual):
                                return False
                        elif any(_safe_eq(actual, item) for item in val):
                            return False
                    elif op == "$gt":
                        if actual is None or actual <= val:
                            return False
                    elif op == "$gte":
                        if actual is None or actual < val:
                            return False
                    elif op == "$lt":
                        if actual is None or actual >= val:
                            return False
                    elif op == "$lte":
                        if actual is None or actual > val:
                            return False
                    elif op == "$exists":
                        exists = _get_nested(doc, key) is not None or key in doc
                        if bool(exists) != bool(val):
                            return False
                    elif op == "$size":
                        if not isinstance(actual, (list, tuple, set)) or len(actual) != int(val):
                            return False
                    elif op == "$all":
                        if not isinstance(actual, (list, tuple, set)):
                            return False
                        if not all(any(_safe_eq(item, target) for item in actual) for target in val):
                            return False
                    elif op == "$elemMatch":
                        if not isinstance(actual, (list, tuple)):
                            return False
                        if not any(
                            isinstance(elem, dict) and PyMongoInstructionParser.match_document(elem, val)
                            for elem in actual
                        ):
                            return False
                    elif op == "$regex":
                        if actual is None:
                            return False
                        pattern = val
                        flags = 0
                        if "$options" in expected and "i" in expected["$options"]:
                            flags = re.IGNORECASE
                        if isinstance(pattern, re.Pattern):
                            if not pattern.search(str(actual)):
                                return False
                        elif not re.search(pattern, str(actual), flags=flags):
                            return False
                    elif op == "$not":
                        if isinstance(val, dict):
                            sub_doc = {key: actual}
                            sub_q = {key: val}
                            if PyMongoInstructionParser.match_document(sub_doc, sub_q):
                                return False
            elif isinstance(expected, re.Pattern):
                if actual is None or not expected.search(str(actual)):
                    return False
            else:
                if isinstance(actual, (list, tuple, set)):
                    if not any(_safe_eq(item, expected) for item in actual):
                        return False
                elif not _safe_eq(actual, expected):
                    return False

        return True

    @staticmethod
    def apply_update(doc: Dict[str, Any], update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply MongoDB update instructions ($set, $unset, $addToSet, $push, $pull, $pullAll,
        $inc, $min, $max, $pop, $rename, $currentDate) to a document in-place.
        """
        if not update:
            return doc

        has_operators = any(k.startswith("$") for k in update.keys())
        if not has_operators:
            doc.update(update)
            return doc

        # $set
        if "$set" in update and isinstance(update["$set"], dict):
            for k, v in update["$set"].items():
                _set_nested(doc, k, v)

        # $unset
        if "$unset" in update and isinstance(update["$unset"], (dict, list)):
            keys_to_unset = update["$unset"].keys() if isinstance(update["$unset"], dict) else update["$unset"]
            for k in keys_to_unset:
                _unset_nested(doc, k)

        # $inc
        if "$inc" in update and isinstance(update["$inc"], dict):
            for k, delta in update["$inc"].items():
                current = _get_nested(doc, k)
                if current is None:
                    current = 0
                try:
                    _set_nested(doc, k, current + delta)
                except TypeError:
                    _set_nested(doc, k, delta)

        # $min
        if "$min" in update and isinstance(update["$min"], dict):
            for k, val in update["$min"].items():
                current = _get_nested(doc, k)
                if current is None or val < current:
                    _set_nested(doc, k, val)

        # $max
        if "$max" in update and isinstance(update["$max"], dict):
            for k, val in update["$max"].items():
                current = _get_nested(doc, k)
                if current is None or val > current:
                    _set_nested(doc, k, val)

        # $rename
        if "$rename" in update and isinstance(update["$rename"], dict):
            for old_k, new_k in update["$rename"].items():
                if old_k in doc:
                    doc[new_k] = doc.pop(old_k)

        # $currentDate
        if "$currentDate" in update and isinstance(update["$currentDate"], dict):
            now = time.time()
            for k, _ in update["$currentDate"].items():
                _set_nested(doc, k, now)

        # $addToSet
        if "$addToSet" in update and isinstance(update["$addToSet"], dict):
            for k, val in update["$addToSet"].items():
                lst = _get_nested(doc, k)
                if lst is None or not isinstance(lst, list):
                    lst = [] if lst is None else [lst]
                    _set_nested(doc, k, lst)
                if isinstance(val, dict) and "$each" in val:
                    for item in val["$each"]:
                        if not any(_safe_eq(x, item) for x in lst):
                            lst.append(item)
                elif not any(_safe_eq(x, val) for x in lst):
                    lst.append(val)

        # $push
        if "$push" in update and isinstance(update["$push"], dict):
            for k, val in update["$push"].items():
                lst = _get_nested(doc, k)
                if lst is None or not isinstance(lst, list):
                    lst = [] if lst is None else [lst]
                    _set_nested(doc, k, lst)
                if isinstance(val, dict) and "$each" in val:
                    items_to_push = list(val["$each"])
                    pos = val.get("$position")
                    if pos is not None and isinstance(pos, int):
                        for item in reversed(items_to_push):
                            lst.insert(pos, item)
                    else:
                        lst.extend(items_to_push)
                    slice_len = val.get("$slice")
                    if slice_len is not None and isinstance(slice_len, int):
                        if slice_len < 0:
                            lst[:] = lst[slice_len:]
                        else:
                            lst[:] = lst[:slice_len]
                else:
                    lst.append(val)

        # $pull
        if "$pull" in update and isinstance(update["$pull"], dict):
            for k, val in update["$pull"].items():
                lst = _get_nested(doc, k)
                if isinstance(lst, list):
                    if isinstance(val, dict):
                        doc[k] = [
                            x for x in lst
                            if not (isinstance(x, dict) and PyMongoInstructionParser.match_document(x, val))
                        ]
                    else:
                        doc[k] = [x for x in lst if not _safe_eq(x, val)]

        # $pullAll
        if "$pullAll" in update and isinstance(update["$pullAll"], dict):
            for k, vals in update["$pullAll"].items():
                lst = _get_nested(doc, k)
                if isinstance(lst, list) and isinstance(vals, (list, tuple, set)):
                    doc[k] = [x for x in lst if not any(_safe_eq(x, v) for v in vals)]

        # $pop
        if "$pop" in update and isinstance(update["$pop"], dict):
            for k, val in update["$pop"].items():
                lst = _get_nested(doc, k)
                if isinstance(lst, list) and lst:
                    if int(val) < 0:
                        lst.pop(0)
                    else:
                        lst.pop()

        return doc

    @staticmethod
    def to_sql_where(
        query: Dict[str, Any], dialect: str = "sqlite"
    ) -> Tuple[str, List[Any]]:
        """
        Translate a MongoDB query into a safe parameterized SQL WHERE clause
        for SQLite or PostgreSQL.
        Complex/untranslatable operators fall back to in-memory evaluation.
        """
        if not query:
            return "", []

        # If logical root operators are present, defer to in-memory match_document
        if any(k.startswith("$") for k in query.keys()):
            return "", []

        clauses: List[str] = []
        params: List[Any] = []
        is_pg = dialect.lower() in ("postgresql", "postgres")

        for key, expected in query.items():
            if key == "_id":
                if isinstance(expected, dict) and "$in" in expected and isinstance(expected["$in"], (list, tuple)):
                    in_items = expected["$in"]
                    if not in_items:
                        clauses.append("1 = 0")
                        continue
                    in_placeholders = []
                    for item in in_items:
                        ph = f"${len(params) + 1}" if is_pg else "?"
                        in_placeholders.append(ph)
                        params.append(str(item))
                    clauses.append(f"_id IN ({', '.join(in_placeholders)})")
                elif not isinstance(expected, dict):
                    placeholder = f"${len(params) + 1}" if is_pg else "?"
                    clauses.append(f"_id = {placeholder}")
                    params.append(str(expected))
            else:
                # Sanitize key name to prevent SQL injection in json path
                if not re.match(r"^[a-zA-Z0-9_\.]+$", key):
                    continue

                if is_pg:
                    json_expr = f"data->>'{key}'"
                    placeholder = f"${len(params) + 1}"
                else:
                    json_expr = f"json_extract(data, '$.{key}')"
                    placeholder = "?"

                if isinstance(expected, dict):
                    if "$ne" in expected:
                        clauses.append(f"{json_expr} != {placeholder}")
                        val = expected["$ne"]
                        params.append(str(val) if not isinstance(val, (int, float, bool)) else val)
                    elif "$gt" in expected and isinstance(expected["$gt"], (int, float)):
                        clauses.append(f"CAST({json_expr} AS NUMERIC) > {placeholder}")
                        params.append(expected["$gt"])
                    elif "$gte" in expected and isinstance(expected["$gte"], (int, float)):
                        clauses.append(f"CAST({json_expr} AS NUMERIC) >= {placeholder}")
                        params.append(expected["$gte"])
                    elif "$lt" in expected and isinstance(expected["$lt"], (int, float)):
                        clauses.append(f"CAST({json_expr} AS NUMERIC) < {placeholder}")
                        params.append(expected["$lt"])
                    elif "$lte" in expected and isinstance(expected["$lte"], (int, float)):
                        clauses.append(f"CAST({json_expr} AS NUMERIC) <= {placeholder}")
                        params.append(expected["$lte"])
                elif isinstance(expected, (int, float, bool, str)):
                    clauses.append(f"{json_expr} = {placeholder}")
                    params.append(str(expected) if isinstance(expected, str) else expected)

        if not clauses:
            return "", []

        return " WHERE " + " AND ".join(clauses), params
