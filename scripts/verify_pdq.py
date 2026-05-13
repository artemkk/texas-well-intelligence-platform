"""
P-TWIP-015-VERIFY-AUTO: Automated PDQ verification of production parser.
Queries RRC PDQ system for 10 selected tuples and compares to parsed output.
"""

from playwright.sync_api import sync_playwright
import time
import json
import os

TUPLES = [
    # (district, lease_number, prod_year, prod_month, parsed_oil, parsed_gas, category)
    ('11', '003137', '2023', '03', 859389, 2985212, 'HIGH'),
    ('01', '017339', '2023', '03', 548848, 0, 'HIGH'),
    ('10', '046263', '2022', '07', 517391, 1250347, 'HIGH'),
    ('03', '026879', '2021', '05', 408, 5600, 'MODERATE'),
    ('09', '017838', '2021', '11', 25, 80, 'MODERATE'),
    ('14', '008148', '2021', '11', 109, 1906, 'MODERATE'),
    ('08', '026346', '2023', '01', 1, 44, 'LOW'),
    ('05', '002765', '2022', '08', 2, 0, 'LOW'),
    ('13', '033736', '2022', '08', 18, 2229, 'GAS_DOM'),
    ('06', '004589', '2022', '02', 25, 550, 'GAS_DOM'),
]

MONTH_NAMES = {
    '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
    '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
    '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
}


def parse_int(s):
    """Parse integer from PDQ display (may have commas)"""
    s = s.strip().replace(',', '')
    if not s or s == '-':
        return 0
    return int(s)


def month_label(month_str, year_str):
    """Build expected label like 'May 2021'"""
    return f"{MONTH_NAMES[month_str]} {year_str}"


def run_verification():
    results = []

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        for i, (dist, lease, year, month, parsed_oil, parsed_gas, cat) in enumerate(TUPLES):
            # PDQ requires 5-digit lease numbers with leading zeros
            lease_stripped = lease[-5:] if len(lease) > 5 else lease
            expected_label = month_label(month, year)

            print(f"\nTuple {i+1}/{len(TUPLES)}: Dist={dist} Lease={lease_stripped} {expected_label} [{cat}]")

            try:
                # Navigate to query form fresh each time
                page.goto(
                    'https://webapps.rrc.texas.gov/PDQ/quickLeaseReportBuilderAction.do',
                    timeout=30000
                )
                time.sleep(2)

                # Fill form
                page.click('input[name=wellType][value=Oil]')
                page.select_option('select[name=district]', dist)
                page.fill('input[name=leaseNumber]', lease_stripped)
                page.select_option('select[name=startMonth]', month)
                page.select_option('select[name=startYear]', year)
                page.select_option('select[name=endMonth]', month)
                page.select_option('select[name=endYear]', year)

                page.click('input[name=submit][value=Submit]')
                time.sleep(4)

                title = page.title()

                if 'Results' not in title:
                    body = page.query_selector('body').text_content()
                    if 'invalid' in body.lower():
                        print(f"  ERROR: Lease number invalid")
                        results.append({
                            'tuple': i+1, 'district': dist, 'lease': lease,
                            'year': year, 'month': month, 'parsed_oil': parsed_oil,
                            'parsed_gas': parsed_gas, 'category': cat,
                            'status': 'INVALID_LEASE', 'pdq_oil': None, 'pdq_gas': None,
                            'operator': '', 'operator_no': '', 'field': ''
                        })
                        continue
                    else:
                        print(f"  ERROR: Unexpected page: {title}")
                        results.append({
                            'tuple': i+1, 'district': dist, 'lease': lease,
                            'year': year, 'month': month, 'parsed_oil': parsed_oil,
                            'parsed_gas': parsed_gas, 'category': cat,
                            'status': 'UNEXPECTED_PAGE', 'pdq_oil': None, 'pdq_gas': None,
                            'operator': '', 'operator_no': '', 'field': ''
                        })
                        continue

                # Parse result table
                grid = page.query_selector('table.DataGrid')
                if not grid:
                    print(f"  ERROR: No DataGrid table found")
                    results.append({
                        'tuple': i+1, 'district': dist, 'lease': lease,
                        'year': year, 'month': month, 'parsed_oil': parsed_oil,
                        'parsed_gas': parsed_gas, 'category': cat,
                        'status': 'NO_TABLE', 'pdq_oil': None, 'pdq_gas': None,
                        'operator': '', 'operator_no': '', 'field': ''
                    })
                    continue

                rows = grid.query_selector_all('tr')
                data_found = False
                pdq_oil = None
                pdq_gas = None
                operator_name = ''
                operator_no = ''
                field_name = ''

                for row in rows[2:]:  # Skip 2 header rows
                    cells = row.query_selector_all('td')
                    if len(cells) < 9:
                        continue
                    date_text = cells[0].text_content().strip()
                    if 'Total' in date_text:
                        continue

                    # Check if this is our month
                    if expected_label in date_text:
                        pdq_oil = parse_int(cells[1].text_content())
                        pdq_gas = parse_int(cells[3].text_content())
                        operator_name = cells[5].text_content().strip()
                        operator_no = cells[6].text_content().strip()
                        field_name = cells[7].text_content().strip()
                        data_found = True
                        break

                if not data_found:
                    print(f"  NOT FOUND in PDQ for {expected_label}")
                    results.append({
                        'tuple': i+1, 'district': dist, 'lease': lease,
                        'year': year, 'month': month, 'parsed_oil': parsed_oil,
                        'parsed_gas': parsed_gas, 'category': cat,
                        'status': 'NOT_FOUND', 'pdq_oil': None, 'pdq_gas': None,
                        'operator': '', 'operator_no': '', 'field': ''
                    })
                    continue

                # Compare
                oil_match = (pdq_oil == parsed_oil)
                gas_match = (pdq_gas == parsed_gas)

                if oil_match and gas_match:
                    status = 'PASS'
                elif not oil_match and not gas_match:
                    status = 'FAIL_MULTIPLE'
                elif not oil_match:
                    status = 'FAIL_OIL'
                else:
                    status = 'FAIL_GAS'

                print(f"  PDQ: Oil={pdq_oil:,} Gas={pdq_gas:,}  Parsed: Oil={parsed_oil:,} Gas={parsed_gas:,}")
                print(f"  Oil match: {oil_match}  Gas match: {gas_match}  -> {status}")
                print(f"  Operator: {operator_name} ({operator_no}) Field: {field_name}")

                results.append({
                    'tuple': i+1, 'district': dist, 'lease': lease,
                    'year': year, 'month': month, 'parsed_oil': parsed_oil,
                    'parsed_gas': parsed_gas, 'category': cat,
                    'status': status, 'pdq_oil': pdq_oil, 'pdq_gas': pdq_gas,
                    'operator': operator_name, 'operator_no': operator_no,
                    'field': field_name
                })

            except Exception as e:
                print(f"  EXCEPTION: {e}")
                results.append({
                    'tuple': i+1, 'district': dist, 'lease': lease,
                    'year': year, 'month': month, 'parsed_oil': parsed_oil,
                    'parsed_gas': parsed_gas, 'category': cat,
                    'status': f'ERROR:{str(e)[:80]}', 'pdq_oil': None, 'pdq_gas': None,
                    'operator': '', 'operator_no': '', 'field': ''
                })

            time.sleep(1)  # Rate limiting courtesy

        browser.close()

    # Print summary
    print("\n" + "=" * 130)
    print("VERIFICATION SUMMARY")
    print("=" * 130)
    header = f"{'#':>2} | {'Dist':>4} | {'Lease':>8} | {'Year':>4} | {'Mon':>3} | {'Cat':>8} | {'Parsed Oil':>12} | {'PDQ Oil':>12} | {'Parsed Gas':>12} | {'PDQ Gas':>12} | Status"
    print(header)
    print("-" * 130)

    pass_count = 0
    fail_count = 0
    for r in results:
        pdq_oil_str = f"{r['pdq_oil']:>12,}" if r['pdq_oil'] is not None else "         N/A"
        pdq_gas_str = f"{r['pdq_gas']:>12,}" if r['pdq_gas'] is not None else "         N/A"
        print(f"{r['tuple']:>2} | {r['district']:>4} | {r['lease']:>8} | {r['year']:>4} | {r['month']:>3} | {r['category']:>8} | {r['parsed_oil']:>12,} | {pdq_oil_str} | {r['parsed_gas']:>12,} | {pdq_gas_str} | {r['status']}")
        if r['status'] == 'PASS':
            pass_count += 1
        else:
            fail_count += 1

    print(f"\nResult: {pass_count}/10 PASS, {fail_count}/10 non-PASS")
    if pass_count == 10:
        print("VERDICT: PARSER CONFIRMED CORRECT - production data trusted")
    elif fail_count > 0:
        print("VERDICT: INVESTIGATION NEEDED - see details above")

    # Save results JSON
    os.makedirs('data/raw/_pdq_verification', exist_ok=True)
    with open('data/raw/_pdq_verification/results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\nResults saved to data/raw/_pdq_verification/results.json")

    return results


if __name__ == '__main__':
    run_verification()
