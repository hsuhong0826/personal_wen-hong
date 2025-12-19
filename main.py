"""
合約處理複合代理系統 - 主程式

使用 Semantic Kernel 和 Magentic Orchestration 模式
整合 Azure AI Foundry 上的三個代理程式
"""
import asyncio
import sys
import io
import httpx
import warnings
import urllib3

# 設定標準輸出編碼為 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 禁用 SSL 警告（僅用於測試/開發環境）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings("ignore", message="Unverified HTTPS request")

from semantic_kernel import Kernel
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion

from config import load_config
from orchestration import ContractMagenticOrchestrator


async def setup_kernel() -> Kernel:
    """
    設定 Semantic Kernel - 包含 SSL 修正

    Returns:
        配置好的 Kernel 實例
    """
    config = load_config()

    # 創建 Kernel
    kernel = Kernel()

    # 創建自訂的 HTTP client，跳過 SSL 驗證（僅用於測試/開發環境）
    from openai import AsyncAzureOpenAI

    http_client = httpx.AsyncClient(
        verify=False,  # 跳過 SSL 驗證
        timeout=60.0
    )

    # 創建 Azure OpenAI client
    azure_openai_client = AsyncAzureOpenAI(
        azure_endpoint=config.azure_openai_endpoint,
        api_key=config.azure_openai_api_key,
        api_version=config.azure_openai_api_version,
        http_client=http_client,
    )

    # 添加 Azure OpenAI 聊天完成服務
    chat_service = AzureChatCompletion(
        service_id="chat",
        deployment_name=config.azure_openai_deployment_name,
        async_client=azure_openai_client,
    )

    kernel.add_service(chat_service)

    return kernel


async def example_contract_comparison():
    """範例 1: 比對多個合約"""
    print("\n" + "="*80)
    print("範例 1: 合約比對")
    print("="*80)

    kernel = await setup_kernel()
    orchestrator = ContractMagenticOrchestrator(kernel)

    # 模擬兩份合約
    contract1 = """
    合約編號: C-2025-001
    甲方: ABC科技有限公司
    乙方: XYZ軟體開發公司

    第一條 合約期限
    本合約自2025年1月1日起至2025年12月31日止，為期一年。

    第二條 服務內容
    乙方應提供軟體開發服務，包括但不限於：
    1. 系統設計與開發
    2. 測試與部署
    3. 維護與支援

    第三條 報酬
    甲方應支付乙方總計新台幣500萬元整。
    付款方式：分三期支付，第一期200萬，第二期200萬，第三期100萬。
    """

    contract2 = """
    合約編號: C-2025-002
    甲方: ABC科技有限公司
    乙方: DEF系統整合公司

    第一條 合約期限
    本合約自2025年2月1日起至2026年1月31日止，為期一年。

    第二條 服務內容
    乙方應提供系統整合服務，包括：
    1. 系統架構設計
    2. 第三方系統整合
    3. 測試與上線
    4. 技術支援與維護

    第三條 報酬
    甲方應支付乙方總計新台幣600萬元整。
    付款方式：依實際進度分四期支付，各期150萬。
    """

    result = await orchestrator.process_request(
        user_request="請比對這兩份合約，找出關鍵差異",
        contracts=[contract1, contract2]
    )

    print("\n📊 最終結果:")
    print(result["final_result"])


async def example_contract_query():
    """範例 2: 查詢合約資訊"""
    print("\n" + "="*80)
    print("範例 2: 合約查詢")
    print("="*80)

    kernel = await setup_kernel()
    orchestrator = ContractMagenticOrchestrator(kernel)

    contract = """
    軟體授權合約

    第一條 授權範圍
    本授權允許被授權人在最多10台電腦上安裝和使用本軟體。

    第二條 授權期限
    本授權自2025年1月1日起永久有效。

    第三條 限制
    被授權人不得：
    1. 反向工程、反編譯或反組譯本軟體
    2. 出租、出借或轉授權本軟體
    3. 移除或修改本軟體的任何版權聲明

    第四條 保固
    授權人保證本軟體在正常使用情況下，90天內無重大缺陷。
    """

    result = await orchestrator.process_request(
        user_request="這份授權合約的授權範圍和限制是什麼？",
        contracts=[contract],
        context={"question": "授權範圍和限制"}
    )

    print("\n📊 最終結果:")
    print(result["final_result"])


async def example_contract_translation():
    """範例 3: 翻譯合約"""
    print("\n" + "="*80)
    print("範例 3: 合約翻譯")
    print("="*80)

    kernel = await setup_kernel()
    orchestrator = ContractMagenticOrchestrator(kernel)

    english_contract = """
    請將這份英文合約翻譯成繁體中文
    LICENSE AGREEMENT

    Article 1 - Grant of License
    This Agreement grants the Licensee a non-exclusive, non-transferable license
    to use the Software on up to 5 devices.

    Article 2 - Term
    This license is effective from January 1, 2025 and shall remain in effect
    for a period of one (1) year.

    Article 3 - Fees
    The total license fee is USD 10,000, payable in advance.
    """

    result = await orchestrator.process_request(
        user_request="請將這份英文合約翻譯成繁體中文",
        contracts=[english_contract],
        context={"source_lang": "英文", "target_lang": "繁體中文"}
    )

    print("\n📊 最終結果:")
    print(result["final_result"])


async def example_complex_task():
    """範例 4: 複雜任務 - 比對、查詢、翻譯"""
    print("\n" + "="*80)
    print("範例 4: 複雜任務（多代理協作）")
    print("="*80)

    kernel = await setup_kernel()
    orchestrator = ContractMagenticOrchestrator(kernel)

    contracts = [
        """
        中文合約
        第一條: 本合約期限為2025年全年
        第二條: 總金額500萬元
        """,
        """
        English Contract
        Article 1: Term from Jan 2025 to Dec 2025
        Article 2: Total amount USD 150,000
        """
    ]

    result = await orchestrator.process_request(
        user_request="請比對這兩份合約，找出金額差異，並將英文合約翻譯成繁體中文",
        contracts=contracts
    )

    print("\n📊 最終結果:")
    print(result["final_result"])


async def interactive_mode():
    """互動模式"""
    print("\n" + "="*80)
    print("🤖 合約處理助手 - 互動模式")
    print("="*80)
    print("\n輸入 'quit' 或 'exit' 離開\n")

    kernel = await setup_kernel()
    orchestrator = ContractMagenticOrchestrator(kernel)

    while True:
        user_input = input("\n請輸入您的請求: ").strip()

        if user_input.lower() in ['quit', 'exit', '離開', '退出']:
            print("👋 再見！")
            break

        if not user_input:
            continue

        # 這裡可以讓使用者輸入合約內容
        print("\n請輸入合約內容（輸入空行結束）：")
        contracts = []
        current_contract = []

        while True:
            line = input()
            if not line:
                if current_contract:
                    contracts.append("\n".join(current_contract))
                break
            current_contract.append(line)

        if not contracts:
            contracts = None

        result = await orchestrator.process_request(
            user_request=user_input,
            contracts=contracts
        )

        print("\n" + "="*80)
        print("📊 處理結果:")
        print("="*80)
        print(result["final_result"])


async def main():
    """主函數"""
    print("\n" + "="*80)
    print("🚀 合約處理複合代理系統")
    print("使用 Semantic Kernel + Magentic Orchestration")
    print("="*80)

    # 執行範例
    print("\n選擇執行模式：")
    print("1. 範例 1: 合約比對")
    print("2. 範例 2: 合約查詢")
    print("3. 範例 3: 合約翻譯")
    print("4. 範例 4: 複雜任務（多代理協作）")
    print("5. 互動模式")
    print("6. 執行所有範例")

    choice = input("\n請選擇 (1-6): ").strip()

    if choice == "1":
        await example_contract_comparison()
    elif choice == "2":
        await example_contract_query()
    elif choice == "3":
        await example_contract_translation()
    elif choice == "4":
        await example_complex_task()
    elif choice == "5":
        await interactive_mode()
    elif choice == "6":
        await example_contract_comparison()
        await example_contract_query()
        await example_contract_translation()
        await example_complex_task()
    else:
        print("無效的選擇")


if __name__ == "__main__":
    asyncio.run(main())
