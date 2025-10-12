"""
FNQuery Engine: The heart of the scene query system.

This module provides the core function `execute_query` which is responsible for
parsing an FNQuery string and filtering a DatablockProxy tree based on its rules.
"""

import fnmatch
import re
from ..proxy_types import DatablockProxy
from .. import logger
from . import constants

# --- Pre-compiled Regex and Type Maps for Performance ---

# A case-insensitive map for type lookups, created once on module load.
# This prevents case-sensitivity issues (e.g., 'SUNLIGHT' vs 'SunLight').
_LOWERCASE_TYPE_MAP = {k.lower(): v for k, v in constants.BLENDER_TO_FN_TYPE.items()}

FILTER_PARSER_REGEX = re.compile(r"([\w\.]+)\s*(!=|>=|<=|in|=|>|<)\s*(.*)")

def _get_nested_property(proxy: DatablockProxy, key: str, proxy_map: dict):
    """Safely gets a value from a proxy's properties, handling nested and relational keys."""
    try:
        if '.' in key:
            parts = key.split('.', 1)
            rel_name = parts[0]
            rel_target_key = parts[1]
            relationships = proxy.properties.get('_fn_relationships', {})
            rel_path = relationships.get(rel_name)
            if not rel_path: return None
            target_proxy = proxy_map.get(rel_path)
            if not target_proxy: return None
            return _get_nested_property(target_proxy, rel_target_key, proxy_map)
        
        if key == 'type':
            raw_type = proxy.properties.get('datablock_type')
            if not raw_type: return None
            # Use the case-insensitive map for robust type conversion.
            return _LOWERCASE_TYPE_MAP.get(raw_type.lower(), raw_type)

        return proxy.properties.get(key)

    except (KeyError, IndexError, TypeError):
        return None

def _convert_path_to_regex(pattern):
    """Converts a path pattern with Gaffer-style wildcards to a regex."""
    regex_pattern = re.escape(pattern).replace('\\*', '[^/]*').replace('\\.\\.\\.', '.*')
    return f"^{regex_pattern}$"

def execute_query(root_proxy: DatablockProxy, query_string: str) -> list[DatablockProxy]:
    """
    Parses the FNQuery string and filters the proxy tree.
    """
    if not query_string or not root_proxy:
        return []

    # logger.log(f"[QueryEngine] Executing query: '{query_string}'")

    query_parts = query_string.split(',')
    final_results = {}
    all_proxies = root_proxy.get_flat_list()
    proxy_map = {p.path: p for p in all_proxies}

    for part in query_parts:
        part = part.strip()
        if not part: continue

        first_bracket = part.find('[')
        if first_bracket == -1:
            path_pattern = part
            filters_str = ""
        else:
            path_pattern = part[:first_bracket]
            filters_str = part[first_bracket:]
        
        filters = re.findall(r"\[(.*?)\]", filters_str)

        # logger.log(f"[QueryEngine]  - Parsed Path: '{path_pattern}'")
        # logger.log(f"[QueryEngine]  - Parsed Filters: {filters}")

        path_matches = []
        if '...' in path_pattern:
            regex = _convert_path_to_regex(path_pattern)
            path_matches = [p for p in all_proxies if re.match(regex, p.path)]
        else:
            path_matches = [p for p in all_proxies if fnmatch.fnmatch(p.path, path_pattern)]

        filtered_matches = []
        for proxy in path_matches:
            all_filters_match = True
            for f_str in filters:
                filter_match = FILTER_PARSER_REGEX.match(f_str)
                if not filter_match: continue

                key, op, val_str = filter_match.groups()
                val_str = val_str.strip('\'"')

                if key == 'member_of':
                    collection_links = proxy.properties.get('_fn_relationships', {}).get('collection_links', [])
                    target_cols = execute_query(root_proxy, val_str)
                    target_col_paths = {p.path for p in target_cols}
                    
                    if op == '=' and not any(p in collection_links for p in target_col_paths):
                        all_filters_match = False
                    elif op == 'in':
                        found = False
                        for col_path in collection_links:
                            curr = proxy_map.get(col_path)
                            while curr:
                                if curr.path in target_col_paths: found = True; break
                                curr = curr.parent
                            if found: break
                        if not found: all_filters_match = False
                    
                    if not all_filters_match: break
                    continue

                proxy_val = _get_nested_property(proxy, key, proxy_map)
                if proxy_val is None: 
                    all_filters_match = False
                    break

                try:
                    if isinstance(proxy_val, (int, float)): val = float(val_str)
                    elif isinstance(proxy_val, bool): val = val_str.lower() in ['true', '1']
                    else: val = val_str
                except ValueError: 
                    all_filters_match = False
                    break

                if op == '=' and not proxy_val == val: all_filters_match = False
                elif op == '!=' and not proxy_val != val: all_filters_match = False
                elif op == '>' and not proxy_val > val: all_filters_match = False
                elif op == '<' and not proxy_val < val: all_filters_match = False
                elif op == '>=' and not proxy_val >= val: all_filters_match = False
                elif op == '<=' and not proxy_val <= val: all_filters_match = False
                
                if not all_filters_match: break

            if all_filters_match:
                filtered_matches.append(proxy)

        for proxy in filtered_matches:
            final_results[proxy.fn_uuid] = proxy

    # logger.log(f"[QueryEngine] Query '{query_string}' matched {len(final_results)} unique proxies.")
    return list(final_results.values())