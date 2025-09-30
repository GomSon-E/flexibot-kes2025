from pymodbus.client import ModbusTcpClient
import time

client = ModbusTcpClient('192.168.1.100', port=502)

if client.connect():
    print("✓ 피더 연결 성공!")
    
    # 현재 상태 읽기
    result = client.read_holding_registers(0, count=15)
    
    if hasattr(result, 'registers'):
        print(f"\n[초기 상태]")
        print(f"  스위치: {result.registers[0]}")
        print(f"  동작번호: {result.registers[1]}")
        print(f"  조명1: {result.registers[10]} (밝기: {result.registers[11]})")
        
        # 조명 켜기 (밝기 50%)
        print("\n조명 켜기")
        client.write_register(10, 1)      # 조명 ON
        client.write_register(11, 100)    # 밝기 10%
        time.sleep(1)
        
        # 집합 동작 3초
        print("\n집합 동작 3초")
        client.write_register(1, 10113)   # 표준동작(1), 그룹1, 집합(14)
        client.write_register(0, 1)       # 시작
        time.sleep(1)
        client.write_register(0, 0)       # 정지

        client.write_register(1, 10114)   # 표준동작(1), 그룹1, 집합(14)
        client.write_register(0, 1)       # 시작
        time.sleep(3)
        client.write_register(0, 0)       # 정지
        
        # 조명 끄기
        print("\n조명 끄기")
        # client.write_register(10, 0)
        
        print("\n완료!")
    else:
        print(f"오류: {result}")
    
    client.close()
else:
    print("✗ 연결 실패")