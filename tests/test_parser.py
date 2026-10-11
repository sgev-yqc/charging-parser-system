"""Small protocol fixtures with no customer file or order data."""

import unittest

from charging_parser.parser import parse_file_content


def can_line(timestamp_ms, can_id, data):
    timestamp = f"2026-01-01 00:00:00.{timestamp_ms:03d}"
    return f"{timestamp} {can_id:08x} " + " ".join(f"{byte:02x}" for byte in data)


def transport_lines(pgn, payload, start_ms):
    packet_count = (len(payload) + 6) // 7
    pgn_bytes = pgn.to_bytes(3, "little")
    lines = [
        can_line(start_ms, 0x1CEC56F4,
                 bytes([0x10, len(payload), 0, packet_count, 0xFF]) + pgn_bytes),
        can_line(start_ms + 1, 0x1CEC56F4,
                 bytes([0x11, packet_count, 1, 0xFF, 0xFF]) + pgn_bytes),
    ]
    for index in range(packet_count):
        chunk = payload[index * 7:(index + 1) * 7].ljust(7, b"\xFF")
        lines.append(can_line(start_ms + 2 + index, 0x1CEB56F4,
                              bytes([index + 1]) + chunk))
    lines.append(can_line(start_ms + 2 + packet_count, 0x1CECF456,
                          bytes([0x13, len(payload), 0, packet_count, 0xFF]) + pgn_bytes))
    return lines


class ParserTest(unittest.TestCase):
    def test_transport_frames_and_semantic_messages_are_both_kept(self):
        # 400 V, 10 A, highest cell 3.50 V in group 2, SOC 60%, 45 min.
        bcs = bytes.fromhex("a0 0f 04 10 5e 21 3c 2d 00")
        brm = bytearray(49)
        brm[0:4] = bytes([1, 0, 0, 3])
        bcp = bytes(13)
        lines = (transport_lines(0x0200, brm, 0)
                 + transport_lines(0x0600, bcp, 20)
                 + transport_lines(0x1100, bcs, 40))

        results = parse_file_content("\n".join(lines).encode())
        names = [result["name"] for result in results]
        self.assertEqual(names.count("BRM"), 1)
        self.assertEqual(names.count("BCP"), 1)
        self.assertEqual(names.count("BCS"), 1)
        self.assertEqual(names.count("TP_DT"), 11)
        self.assertEqual(names.count("TP_CM_REQ"), 6)
        self.assertEqual(names.count("TP_CM_RSP"), 3)

        bcs_index = names.index("BCS")
        self.assertEqual(names[bcs_index - 2:bcs_index + 2],
                         ["TP_DT", "TP_DT", "BCS", "TP_CM_RSP"])
        self.assertIn("原始数据=A0 0F 04 10 5E 21 3C", results[bcs_index - 2]["decoded"])
        self.assertIn("原始数据=2D 00 FF FF FF FF FF", results[bcs_index - 1]["decoded"])
        decoded = results[bcs_index]["decoded"]
        for value in ("400.0V", "10.0A", "3.50V", "组号2", "60%", "45min"):
            self.assertIn(value, decoded)

    def test_incomplete_transport_has_no_semantic_message(self):
        bcs = bytes.fromhex("a0 0f 04 10 5e 21 3c 2d 00")
        lines = transport_lines(0x1100, bcs, 0)[:3]
        names = [result["name"] for result in parse_file_content("\n".join(lines).encode())]
        self.assertEqual(names, ["TP_CM_REQ", "TP_CM_REQ", "TP_DT"])


if __name__ == "__main__":
    unittest.main()
