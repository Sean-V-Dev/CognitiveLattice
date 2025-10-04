#!/usr/bin/env python3
"""
Bulk Test Script for Chipotle Web Automation
Runs the same Chipotle bowl ordering test multiple times to gather performance data.
"""

import asyncio
import json
import os
import sys
import argparse
from datetime import datetime
from typing import Dict, List, Any
import traceback

from core.external_api_client import ExternalAPIClient
from core.cognitive_lattice import CognitiveLattice, SessionManager
from tools.web_automation.cognitive_lattice_web_coordinator import execute_cognitive_web_task

# Test configuration
TEST_COUNT = 40
TEST_PROMPT = (
   "go to chipotle.com. Then go to the menu and build me a bowl with the following ingredients: chicken, white rice, and black beans. Hit add to bag button after that. After that, for the meal name, type \"Sean\". Now, look for the entree and confirm that the ingredients (chicken, white rice and black beans) were selected. Then look for the total and report the price for the order. Finally, click the remove item button."

)

TEST_URL = "https://chipotle.com"

class ChipotleBulkTester:
    """Handles bulk testing of Chipotle web automation."""
    
    def __init__(self, test_count: int = TEST_COUNT):
        self.test_count = test_count
        self.test_results: List[Dict[str, Any]] = []
        self.session_manager = SessionManager()
        
        # Initialize external API client
        try:
            self.external_api = ExternalAPIClient()
            print("🌐 External API client initialized")
        except Exception as e:
            print(f"⚠️ Could not initialize External API Client: {e}")
            self.external_api = None
    
    async def run_single_test(self, test_number: int) -> Dict[str, Any]:
        """Run a single Chipotle automation test and collect results."""
        
        print(f"\n{'='*80}")
        print(f"🧪 STARTING TEST #{test_number:02d}/{self.test_count}")
        print(f"{'='*80}")
        
        test_start_time = datetime.now()
        test_result = {
            "test_number": test_number,
            "start_time": test_start_time.isoformat(),
            "prompt": TEST_PROMPT,
            "url": TEST_URL,
            "success": False,
            "error": None,
            "duration_seconds": 0,
            "steps_completed": 0,
            "total_steps": 0,
            "final_result": "",
            "debug_info": {}
        }
        
        try:
            # Execute the web automation task
            result = await execute_cognitive_web_task(
                goal=TEST_PROMPT,
                url=TEST_URL,
                external_client=self.external_api,
                cognitive_lattice=self.session_manager.lattice
            )
            
            test_end_time = datetime.now()
            duration = (test_end_time - test_start_time).total_seconds()
            
            # Parse result for success indicators
            result_str = str(result)
            
            # Check for success indicators
            success_indicators = [
                "successfully completed",
                "task completed",
                "remove item button",
                "clicked remove",
                "order removed",
                "bowl removed"
            ]
            
            # Check for failure indicators
            failure_indicators = [
                "failed",
                "error",
                "timeout",
                "could not find",
                "unable to",
                "exception"
            ]
            
            has_success = any(indicator in result_str.lower() for indicator in success_indicators)
            has_failure = any(indicator in result_str.lower() for indicator in failure_indicators)
            
            # Determine success based on indicators
            if has_success and not has_failure:
                test_result["success"] = True
            elif result and len(result_str) > 100:  # If we got a substantial result
                test_result["success"] = True
            
            # Extract step information from result
            step_info = self._extract_step_info(result)
            
            # DEBUG: Print result structure to understand what we're getting
            print(f"🐛 DEBUG - Result type: {type(result)}")
            if isinstance(result, dict):
                print(f"🐛 DEBUG - Result keys: {list(result.keys())}")
                if "completed_steps" in result:
                    print(f"🐛 DEBUG - Direct completed_steps: {result['completed_steps']}")
                if "total_steps" in result:
                    print(f"🐛 DEBUG - Direct total_steps: {result['total_steps']}")
            print(f"🐛 DEBUG - Extracted step_info: {step_info}")
            
            test_result.update({
                "end_time": test_end_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "final_result": result_str[:1000] + "..." if len(result_str) > 1000 else result_str,
                "completed_steps": step_info["completed_steps"],
                "total_steps": step_info["total_steps"],
                "step_success_rate": step_info["step_success_rate"]
            })
            
            print(f"✅ TEST #{test_number:02d} COMPLETED in {duration:.1f}s")
            print(f"   Success: {test_result['success']}")
            print(f"   Steps: {step_info['completed_steps']}/{step_info['total_steps']} ({step_info['step_success_rate']*100:.1f}%)")
            print(f"   Result preview: {result_str[:150]}...")
            
        except Exception as e:
            test_end_time = datetime.now()
            duration = (test_end_time - test_start_time).total_seconds()
            
            test_result.update({
                "end_time": test_end_time.isoformat(),
                "duration_seconds": round(duration, 2),
                "success": False,
                "error": str(e),
                "final_result": f"ERROR: {str(e)}",
                "completed_steps": 0,
                "total_steps": 0,
                "step_success_rate": 0.0
            })
            
            print(f"❌ TEST #{test_number:02d} FAILED in {duration:.1f}s")
            print(f"   Error: {str(e)}")
            
            # Print stack trace for debugging
            traceback.print_exc()
        
        return test_result
    
    def _extract_step_info(self, result) -> Dict[str, Any]:
        """Extract step completion information from web automation result."""
        step_info = {
            "completed_steps": 0,
            "total_steps": 0,
            "step_success_rate": 0.0
        }
        
        try:
            # Handle web automation results - they contain completed_steps and total_steps directly
            if isinstance(result, dict):
                # Check for direct step counts (new web automation format)
                if "completed_steps" in result and "total_steps" in result:
                    step_info["completed_steps"] = result.get("completed_steps", 0)
                    step_info["total_steps"] = result.get("total_steps", 0)
                    if step_info["total_steps"] > 0:
                        step_info["step_success_rate"] = step_info["completed_steps"] / step_info["total_steps"]
                    return step_info
                
                # Check for task_results (legacy format)
                elif "task_results" in result:
                    task_results = result["task_results"]
                    if isinstance(task_results, list):
                        step_info["total_steps"] = len(task_results)
                        
                        # Count successful steps
                        successful_steps = 0
                        for step in task_results:
                            if isinstance(step, dict):
                                # Check multiple success indicators
                                step_success = (
                                    step.get("success", False) or
                                    (step.get("result", {}) or {}).get("success", False) or
                                    (step.get("step_successful", False))
                                )
                                if step_success:
                                    successful_steps += 1
                        
                        step_info["completed_steps"] = successful_steps
                        
                        if step_info["total_steps"] > 0:
                            step_info["step_success_rate"] = successful_steps / step_info["total_steps"]
            
            # Fallback: Try to parse from string representation
            elif isinstance(result, (str, dict)):
                result_str = str(result).lower()
                
                # Look for step completion patterns
                import re
                
                # Pattern: "X/Y steps completed" or "X of Y steps"
                step_patterns = [
                    r'(\d+)/(\d+)\s+steps?\s+(?:completed|successful)',
                    r'(\d+)\s+of\s+(\d+)\s+steps?\s+(?:completed|successful)',
                    r'completed\s+(\d+)/(\d+)\s+steps?',
                    r'(\d+)\s+steps?\s+completed.*?(\d+)\s+total'
                ]
                
                for pattern in step_patterns:
                    match = re.search(pattern, result_str)
                    if match:
                        step_info["completed_steps"] = int(match.group(1))
                        step_info["total_steps"] = int(match.group(2))
                        if step_info["total_steps"] > 0:
                            step_info["step_success_rate"] = step_info["completed_steps"] / step_info["total_steps"]
                        break
                
                # If no pattern found, try to count step mentions
                if step_info["total_steps"] == 0:
                    # Count "step X" mentions to estimate total steps
                    step_mentions = re.findall(r'step\s+(\d+)', result_str)
                    if step_mentions:
                        step_info["total_steps"] = max(int(s) for s in step_mentions)
                    
                    # Count success indicators
                    success_mentions = len(re.findall(r'step\s+\d+.*?(?:success|completed|✅)', result_str))
                    step_info["completed_steps"] = success_mentions
                    
                    if step_info["total_steps"] > 0:
                        step_info["step_success_rate"] = step_info["completed_steps"] / step_info["total_steps"]
                        
        except Exception as e:
            # If parsing fails, return zeros
            print(f"⚠️ Failed to extract step info: {e}")
            
        return step_info
    
    def save_results(self, results: List[Dict[str, Any]]):
        """Save test results to a JSON file with timestamp."""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"chipotle_bulk_test_results_{timestamp}.json"
        filepath = os.path.join(os.getcwd(), filename)
        
        # Calculate summary statistics
        successful_tests = [r for r in results if r["success"]]
        failed_tests = [r for r in results if not r["success"]]
        
        if results:
            avg_duration = sum(r["duration_seconds"] for r in results) / len(results)
            min_duration = min(r["duration_seconds"] for r in results)
            max_duration = max(r["duration_seconds"] for r in results)
        else:
            avg_duration = min_duration = max_duration = 0
        
        # Calculate step statistics
        total_steps_across_all_tests = sum(r.get("total_steps", 0) for r in results)
        total_completed_steps = sum(r.get("completed_steps", 0) for r in results)
        step_success_rate = 0.0
        if total_steps_across_all_tests > 0:
            step_success_rate = (total_completed_steps / total_steps_across_all_tests) * 100
        
        summary = {
            "test_summary": {
                "total_tests": len(results),
                "successful_tests": len(successful_tests),
                "failed_tests": len(failed_tests),
                "success_rate": round(len(successful_tests) / len(results) * 100, 1) if results else 0,
                "average_duration_seconds": round(avg_duration, 2),
                "min_duration_seconds": round(min_duration, 2),
                "max_duration_seconds": round(max_duration, 2),
                "total_steps": total_steps_across_all_tests,
                "completed_steps": total_completed_steps,
                "step_success_rate": round(step_success_rate, 1),
                "test_prompt": TEST_PROMPT,
                "test_url": TEST_URL,
                "timestamp": timestamp
            },
            "individual_test_results": results
        }
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(summary, f, indent=2, ensure_ascii=False)
            
            print(f"\n💾 Test results saved to: {filepath}")
            return filepath
            
        except Exception as e:
            print(f"❌ Failed to save results: {e}")
            return None
    
    def print_summary(self, results: List[Dict[str, Any]]):
        """Print a summary of all test results."""
        
        if not results:
            print("❌ No test results to summarize")
            return
        
        successful_tests = [r for r in results if r["success"]]
        failed_tests = [r for r in results if not r["success"]]
        
        avg_duration = sum(r["duration_seconds"] for r in results) / len(results)
        min_duration = min(r["duration_seconds"] for r in results)
        max_duration = max(r["duration_seconds"] for r in results)
        
        # Calculate step statistics
        total_steps_across_all_tests = sum(r.get("total_steps", 0) for r in results)
        total_completed_steps = sum(r.get("completed_steps", 0) for r in results)
        
        # Calculate step success rate
        step_success_rate = 0.0
        if total_steps_across_all_tests > 0:
            step_success_rate = (total_completed_steps / total_steps_across_all_tests) * 100
        
        print(f"\n{'='*80}")
        print(f"📊 BULK TEST SUMMARY")
        print(f"{'='*80}")
        print(f"🎯 TEST LEVEL RESULTS:")
        print(f"Total Tests:        {len(results)}")
        print(f"Successful Tests:   {len(successful_tests)} ({len(successful_tests)/len(results)*100:.1f}%)")
        print(f"Failed Tests:       {len(failed_tests)} ({len(failed_tests)/len(results)*100:.1f}%)")
        
        print(f"\n📋 STEP LEVEL RESULTS:")
        print(f"Total Steps:        {total_steps_across_all_tests}")
        print(f"Completed Steps:    {total_completed_steps}")
        print(f"Step Success Rate:  {step_success_rate:.1f}%")
        
        print(f"\n⏱️ TIMING RESULTS:")
        print(f"Average Duration:   {avg_duration:.1f} seconds")
        print(f"Min Duration:       {min_duration:.1f} seconds")
        print(f"Max Duration:       {max_duration:.1f} seconds")
        
        if failed_tests:
            print(f"\n❌ FAILED TEST NUMBERS:")
            failed_numbers = [str(r["test_number"]).zfill(2) for r in failed_tests]
            print(f"   {', '.join(failed_numbers)}")
            
            # Show common error patterns
            error_messages = [r["error"] for r in failed_tests if r["error"]]
            if error_messages:
                print(f"\n🔍 COMMON ERROR PATTERNS:")
                error_counts = {}
                for error in error_messages:
                    error_key = error[:100]  # First 100 chars
                    error_counts[error_key] = error_counts.get(error_key, 0) + 1
                
                for error, count in sorted(error_counts.items(), key=lambda x: x[1], reverse=True):
                    print(f"   {count}x: {error}...")
        
        # Show step-level breakdown for tests with partial success
        tests_with_partial_steps = [r for r in results if r.get("total_steps", 0) > 0 and r.get("completed_steps", 0) > 0 and r.get("step_success_rate", 0) < 1.0]
        if tests_with_partial_steps:
            print(f"\n📝 PARTIAL SUCCESS BREAKDOWN:")
            for test in tests_with_partial_steps[:10]:  # Show first 10
                test_num = test.get("test_number", "??")
                completed = test.get("completed_steps", 0)
                total = test.get("total_steps", 0)
                rate = test.get("step_success_rate", 0) * 100
                print(f"   Test #{test_num:02d}: {completed}/{total} steps ({rate:.1f}%)")
            if len(tests_with_partial_steps) > 10:
                print(f"   ... and {len(tests_with_partial_steps) - 10} more tests with partial success")
        
        print(f"\n🎯 TEST PROMPT: {TEST_PROMPT}")
        print(f"🌐 TEST URL: {TEST_URL}")
    
    async def run_bulk_tests(self):
        """Run all bulk tests and generate comprehensive results."""
        
        print(f"🚀 STARTING BULK CHIPOTLE AUTOMATION TESTING")
        print(f"📊 Running {self.test_count} tests...")
        print(f"🎯 Test prompt: {TEST_PROMPT}")
        print(f"🌐 Test URL: {TEST_URL}")
        
        bulk_start_time = datetime.now()
        
        # Run all tests
        for test_number in range(1, self.test_count + 1):
            try:
                test_result = await self.run_single_test(test_number)
                self.test_results.append(test_result)
                
                # Small delay between tests to prevent overwhelming the system
                await asyncio.sleep(2)
                
            except KeyboardInterrupt:
                print(f"\n⚠️ Testing interrupted by user at test #{test_number}")
                break
            except Exception as e:
                print(f"❌ Unexpected error in test #{test_number}: {e}")
                # Continue with next test
                continue
        
        bulk_end_time = datetime.now()
        total_duration = (bulk_end_time - bulk_start_time).total_seconds()
        
        print(f"\n🏁 BULK TESTING COMPLETED in {total_duration/60:.1f} minutes")
        
        # Print summary
        self.print_summary(self.test_results)
        
        # Save results
        saved_file = self.save_results(self.test_results)
        
        if saved_file:
            print(f"\n📁 Detailed results available in: {saved_file}")
        
        return self.test_results

async def main():
    """Main function to run bulk testing."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Bulk test Chipotle web automation")
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation prompt")
    parser.add_argument("-c", "--count", type=int, help="Number of tests to run", default=TEST_COUNT)
    args = parser.parse_args()
    
    test_count = args.count
    
    print("🧪 CHIPOTLE WEB AUTOMATION BULK TESTER")
    print("=" * 60)
    
    # Confirm with user
    print(f"This will run {test_count} consecutive tests of the Chipotle ordering automation.")
    print(f"Each test will take approximately 200-250 seconds.")
    print(f"Total estimated time: {test_count * 200 / 60:.0f}-{test_count * 250 / 60:.0f} minutes")

    # Handle confirmation based on flags and terminal type
    if not args.yes:
        if sys.stdin.isatty():
            try:
                confirm = input(f"\nProceed with {test_count} tests? (y/N): ").lower().strip()
                if confirm not in ['y', 'yes']:
                    print("❌ Testing cancelled by user")
                    return
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Testing cancelled by user")
                return
        else:
            print(f"\n🚀 Auto-starting {test_count} tests (non-interactive mode)")
            print("   To cancel, press Ctrl+C")
    else:
        print(f"\n🚀 Auto-starting {test_count} tests (--yes flag provided)")
    
    # Create tester and run bulk tests
    tester = ChipotleBulkTester(test_count)
    
    try:
        results = await tester.run_bulk_tests()
        print(f"\n✅ Bulk testing completed! {len(results)} tests executed.")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ Bulk testing interrupted by user")
        if tester.test_results:
            print(f"📊 Partial results available for {len(tester.test_results)} completed tests")
            tester.print_summary(tester.test_results)
            tester.save_results(tester.test_results)
    
    except Exception as e:
        print(f"❌ Bulk testing failed: {e}")
        traceback.print_exc()
        
        if tester.test_results:
            print(f"📊 Partial results available for {len(tester.test_results)} completed tests")
            tester.print_summary(tester.test_results)
            tester.save_results(tester.test_results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in main execution: {e}")
        traceback.print_exc()
