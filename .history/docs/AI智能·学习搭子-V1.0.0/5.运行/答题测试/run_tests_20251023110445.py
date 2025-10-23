#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest
import sys
import os
import argparse
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..')))

# 导入测试模块
from testRandom import SeleniumRandomModeTests, UnitTestRandomMode
from testSequential import SeleniumSequentialModeTests
from testTimedMode import SeleniumTimedModeTests

def run_specific_tests(test_modules, test_names=None, verbosity=2):
    """
    运行指定的测试模块和测试用例
    
    Args:
        test_modules: 要运行的测试模块列表
        test_names: 要运行的特定测试用例名称列表，如果为None则运行所有测试
        verbosity: 测试输出的详细程度
    
    Returns:
        测试结果对象
    """
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    for test_module in test_modules:
        if test_names:
            for test_name in test_names:
                try:
                    suite.addTest(loader.loadTestsFromName(test_name, test_module))
                except Exception as e:
                    print(f"警告: 无法加载测试 {test_name} 从 {test_module.__name__}: {e}")
        else:
            suite.addTest(loader.loadTestsFromTestCase(test_module))
    
    runner = unittest.TextTestRunner(verbosity=verbosity)
    return runner.run(suite)

def generate_report(result, output_file=None):
    """
    生成测试报告
    
    Args:
        result: 测试结果对象
        output_file: 输出文件路径，如果为None则输出到控制台
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report = []
    report.append("=" * 70)
    report.append(f"测试报告 - {timestamp}")
    report.append("=" * 70)
    report.append(f"运行测试总数: {result.testsRun}")
    report.append(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    report.append(f"失败: {len(result.failures)}")
    report.append(f"错误: {len(result.errors)}")
    report.append("=" * 70)
    
    if result.failures:
        report.append("\n失败的测试:")
        for test, traceback in result.failures:
            report.append(f"\n- {test}")
            report.append(f"{traceback}")
    
    if result.errors:
        report.append("\n错误的测试:")
        for test, traceback in result.errors:
            report.append(f"\n- {test}")
            report.append(f"{traceback}")
    
    report_text = "\n".join(report)
    
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        print(f"测试报告已保存到: {output_file}")
    else:
        print(report_text)
    
    return report_text

def main():
    parser = argparse.ArgumentParser(description='运行学习搭子应用的自动化测试')
    parser.add_argument('--mode', choices=['all', 'random', 'sequential', 'timed'], 
                        default='all', help='指定要运行的测试模式')
    parser.add_argument('--test', help='指定要运行的测试用例名称，多个用逗号分隔')
    parser.add_argument('--report', help='指定测试报告输出文件路径')
    parser.add_argument('--verbosity', type=int, choices=[0, 1, 2], default=2,
                        help='测试输出的详细程度 (0=安静, 1=正常, 2=详细)')
    
    args = parser.parse_args()
    
    # 确定要运行的测试模块
    test_modules = []
    if args.mode == 'all' or args.mode == 'random':
        test_modules.extend([SeleniumRandomModeTests, UnitTestRandomMode])
    if args.mode == 'all' or args.mode == 'sequential':
        test_modules.append(SeleniumSequentialModeTests)
    if args.mode == 'all' or args.mode == 'timed':
        test_modules.append(SeleniumTimedModeTests)
    
    # 解析测试用例名称
    test_names = None
    if args.test:
        test_names = [name.strip() for name in args.test.split(',')]
    
    # 运行测试
    print(f"开始运行测试，模式: {args.mode}")
    start_time = time.time()
    result = run_specific_tests(test_modules, test_names, args.verbosity)
    end_time = time.time()
    
    print(f"\n测试完成，耗时: {end_time - start_time:.2f} 秒")
    
    # 生成报告
    report_file = args.report
    if not report_file and args.mode != 'all':
        # 如果没有指定报告文件，但指定了特定模式，则使用默认文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"test_report_{args.mode}_{timestamp}.txt"
    
    generate_report(result, report_file)
    
    # 返回适当的退出代码
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    sys.exit(main())