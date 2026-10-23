"""Create standalone local PNG/HTML diagnostics from a trajectory summary."""
import argparse
import base64
import csv
import html
import json
from pathlib import Path

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, new_directory


def generate(analysis_directory, output, title, maximum_plot_points):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import numpy as np
    analysis_directory = Path(analysis_directory).resolve(strict=True)
    source_report = analysis_directory / 'analysis.json'
    report = json.loads(source_report.read_text(encoding='utf-8'))
    if report['status'] in {'FAILED', 'NO_FRAMES'}:
        raise ValueError('Failed/empty analysis cannot be published as a completed diagnostic report.')
    maximum = integer(maximum_plot_points, 'maximum_plot_points', 2)
    source_csv = analysis_directory / 'frame-metrics.csv'
    rows = []
    with source_csv.open(encoding='utf-8', newline='') as stream:
        # Fixed-size plot sampling without loading the full trajectory or full CSV.
        reader = csv.DictReader(stream)
        stride = max(1, (report['frames_selected'] + maximum - 1) // maximum)
        last = None
        for index, row in enumerate(reader):
            last = row
            if index % stride == 0 and len(rows) < maximum:
                rows.append(row)
        if last is not None and (not rows or rows[-1] != last):
            if len(rows) == maximum:
                rows[-1] = last
            else:
                rows.append(last)
    if not rows:
        raise ValueError('No frame metrics to report.')
    output = new_directory(output)
    x = [int(row['frame']) for row in rows]
    figure, axes = plt.subplots(2, 1, figsize=(8, 6), layout='constrained', sharex=True)
    definitions = [('quantile_height_angstrom', 'Selected film quantile height\n(angstrom)'),
                   ('rms_grid_roughness_angstrom', 'Occupied-grid RMS roughness\n(angstrom)')]
    for axis, (column, label) in zip(axes, definitions):
        y = [float(row[column]) if row[column] else np.nan for row in rows]
        axis.plot(x, y, marker='o', markersize=3, linewidth=1.3)
        axis.set_ylabel(label, fontsize=10)
        axis.grid(alpha=0.2)
    from matplotlib.ticker import MaxNLocator
    axes[-1].xaxis.set_major_locator(MaxNLocator(integer=True))
    axes[-1].set_xlabel('Stored frame index (not inferred physical time)', fontsize=10)
    figure.suptitle('Local geometry diagnostics — ' + report['configuration']['source_class'], fontsize=12)
    image = output / 'geometry-metrics.png'
    figure.savefig(image, dpi=150)
    plt.close(figure)
    encoded = base64.b64encode(image.read_bytes()).decode('ascii')
    config_text = html.escape(json.dumps(report['configuration'], ensure_ascii=False, indent=2))
    method = ''.join('<li>' + html.escape(value) + '</li>' for value in report['method'].values())
    limits = ''.join('<li>' + html.escape(value) + '</li>' for value in report['limitations'])
    document = '<!doctype html><html lang="en"><meta charset="utf-8"><title>' + html.escape(title) + '</title>'
    document += '<style>body{font:16px system-ui;max-width:1050px;margin:36px auto;padding:0 22px;color:#183047}img{max-width:100%}pre{white-space:pre-wrap;background:#f1f5f8;padding:18px}.status{padding:14px;background:#fff2cc}</style>'
    document += '<h1>' + html.escape(title) + '</h1><p class="status">LOCAL DIAGNOSTIC — scientific acceptance UNVERIFIED</p>'
    document += '<p>Source class: ' + html.escape(report['configuration']['source_class']) + '; analysis status: ' + html.escape(report['status']) + '</p>'
    document += f'<p>Selected frames: {report["frames_selected"]}; plotted points: {len(rows)}. Plot sampling is for display only; original CSV is preserved.</p>'
    document += '<img alt="Configured film-height and grid-roughness diagnostics" src="data:image/png;base64,' + encoded + '">'
    document += '<h2>Explicit analysis configuration</h2><pre>' + config_text + '</pre><h2>Definitions</h2><ul>' + method + '</ul><h2>Limits</h2><ul>' + limits + '</ul>'
    document += '<p>Issues: ' + html.escape(json.dumps(report['issues'], ensure_ascii=False)) + '</p></html>'
    (output / 'report.html').write_text(document, encoding='utf-8')
    receipt = {'generated_utc': utc_now(), 'title': title, 'analysis_source': identity(source_report),
               'metrics_source': identity(source_csv), 'plotted_points': len(rows), 'plot_stride': stride,
               'outputs': [identity(output / name) for name in ['report.html', 'geometry-metrics.png']],
               'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False}
    json_file(output / 'report-manifest.json', receipt)
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-directory', required=True)
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--title', required=True)
    parser.add_argument('--maximum-plot-points', type=int, required=True)
    args = parser.parse_args()
    result = generate(args.analysis_directory, args.output_directory, args.title, args.maximum_plot_points)
    print_receipt(args.output_directory, plotted_points=result['plotted_points'], scientific_acceptance='UNVERIFIED')


if __name__ == '__main__':
    main()
