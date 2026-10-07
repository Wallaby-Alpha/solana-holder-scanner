"""
clustering.py: Wallet Independence and Heuristic Clustering Engine.
Identifies related wallets using common funding sources and synchronized transfer patterns.
Outputs Raw Accumulators vs Cluster-Adjusted Accumulator Counts.
"""

from typing import Dict, Any, List, Set, Tuple, Optional
from collections import defaultdict
from datetime import datetime

class WalletClusteringEngine:
    def __init__(self, sync_window_seconds: int = 120):
        self.sync_window_seconds = sync_window_seconds

    def cluster_wallets(
        self,
        wallets: List[Dict[str, Any]],
        transfers: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Groups wallets into entity clusters.
        Returns mapping: cluster_id -> {
            "cluster_id": str,
            "primary_funder": str,
            "members": Set[str],
            "reason": str,
            "confidence": float
        }
        """
        # Disjoint Set Union (DSU) / Union-Find for wallet graph
        parent: Dict[str, str] = {}
        reason_map: Dict[str, str] = {}

        def find(x: str) -> str:
            if x not in parent:
                parent[x] = x
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]

        def union(x: str, y: str, reason: str):
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry
                reason_map[ry] = reason

        # 1. Cluster by common SOL funding wallet
        funder_groups = defaultdict(list)
        for w in wallets:
            addr = w["address"]
            funder = w.get("funding_wallet")
            if funder:
                funder_groups[funder].append(addr)

        for funder, group in funder_groups.items():
            if len(group) > 1:
                base = group[0]
                for member in group[1:]:
                    union(base, member, f"COMMON_FUNDER:{funder[:8]}")

        # 2. Cluster by synchronized buy transactions
        # If 2+ wallets buy the exact same token within seconds of each other
        buys = [t for t in transfers if t.get("tx_type") == "BUY"]
        buys.sort(key=lambda t: t.get("timestamp", ""))

        for i in range(len(buys)):
            t1 = buys[i]
            addr1 = t1.get("to_address")
            ts1 = self._parse_iso(t1.get("timestamp"))
            if not ts1 or not addr1:
                continue

            for j in range(i + 1, min(i + 15, len(buys))):
                t2 = buys[j]
                addr2 = t2.get("to_address")
                ts2 = self._parse_iso(t2.get("timestamp"))
                if not ts2 or not addr2:
                    continue

                diff = abs((ts2 - ts1).total_seconds())
                if diff <= self.sync_window_seconds and addr1 != addr2:
                    # Synchronized transaction match
                    union(addr1, addr2, "SYNCHRONIZED_BUY_BURST")
                elif diff > self.sync_window_seconds:
                    break

        # Group components into clusters
        cluster_components = defaultdict(set)
        for w in wallets:
            addr = w["address"]
            root = find(addr)
            cluster_components[root].add(addr)

        clusters: Dict[str, Dict[str, Any]] = {}
        cluster_idx = 1
        for root, members in cluster_components.items():
            if len(members) > 1:
                cid = f"cluster_{cluster_idx:03d}"
                reason = reason_map.get(root, "BEHAVIORAL_CO_OCCURRENCE")
                clusters[cid] = {
                    "cluster_id": cid,
                    "primary_funder": root,
                    "members": list(members),
                    "reason": reason,
                    "confidence": 0.85 if "COMMON_FUNDER" in reason else 0.65
                }
                cluster_idx += 1

        return clusters

    def compute_cluster_adjusted_count(
        self,
        accumulating_wallets: List[str],
        clusters: Dict[str, Dict[str, Any]]
    ) -> Tuple[int, int, float]:
        """
        Given a list of accumulating wallet addresses, map them to independent entities.
        Returns: (raw_count, cluster_adjusted_count, independence_ratio)
        """
        raw_count = len(accumulating_wallets)
        if raw_count == 0:
            return 0, 0, 1.0

        # Build address -> cluster_id lookup
        addr_to_cluster = {}
        for cid, info in clusters.items():
            for m in info["members"]:
                addr_to_cluster[m] = cid

        independent_entities: Set[str] = set()
        for addr in accumulating_wallets:
            if addr in addr_to_cluster:
                # Grouped entity
                independent_entities.add(addr_to_cluster[addr])
            else:
                # Independent singleton wallet
                independent_entities.add(addr)

        cluster_adjusted_count = len(independent_entities)
        ratio = cluster_adjusted_count / max(raw_count, 1)
        return raw_count, cluster_adjusted_count, round(ratio, 3)

    def _parse_iso(self, ts_str: Optional[str]) -> Optional[datetime]:
        if not ts_str:
            return None
        try:
            # Strip trailing Z if present for python fromisoformat
            clean_ts = ts_str.replace("Z", "+00:00")
            return datetime.fromisoformat(clean_ts)
        except Exception:
            return None
