class ChainageState:
    def __init__(self):
        self.chainage = 0.0
        self.last_t = None
        self.last_v = 0.0
        self.v_default = 10.0 # 10 m/s default if no GPS

class ChainageTracker:
    """Integrates speed·dt per node → chainage; aligns frames & IMU to 0.25 m bins."""
    def __init__(self):
        self.state = {}
        self.session_ids = {}

    def get_state(self, node_id: str) -> ChainageState:
        if node_id not in self.state:
            self.state[node_id] = ChainageState()
            import uuid
            self.session_ids[node_id] = str(uuid.uuid4())
        return self.state[node_id]

    def update(self, node_id: str, t_ms: float, speed: float = None) -> float:
        st = self.get_state(node_id)
        dt = (t_ms - st.last_t) / 1000.0 if st.last_t else 0.0
        v = speed if speed is not None else st.v_default
        st.chainage += 0.5 * (v + st.last_v) * dt
        st.last_t = t_ms
        st.last_v = v
        return st.chainage

    def peek(self, node_id: str) -> float:
        return self.get_state(node_id).chainage
        
    def session(self, node_id: str) -> str:
        self.get_state(node_id) # ensure created
        return self.session_ids[node_id]

tracker = ChainageTracker()
