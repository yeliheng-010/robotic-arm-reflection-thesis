import argparse
import qualify


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('case_id')
    name=parser.parse_args().case_id
    manifest=qualify.read(qualify.ROOT/'manifest.json')
    assert all(qualify.sha(p)==h for p,h in manifest['identities'].items())
    case=next(c for c in manifest['cases'] if c['item']['id']==name)
    template_path=qualify.SOURCE/'cases/S0_962601_baseline/attempt_2/route.json'
    target=qualify.ROOT/'results'/(name+'.json')
    assert not target.exists()
    row=qualify.qualify(case,qualify.read(template_path)['context'])
    qualify.save(target,row)
    print(row,flush=True)


if __name__=='__main__':
    main()
