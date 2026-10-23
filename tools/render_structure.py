"""Render a local structural preview with OVITO's software renderer."""
import argparse
import os
from pathlib import Path

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, new_directory
from structure_io import validate_order


def render(source, file_format, type_order, output, label, width=1000, height=700):
    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    import ovito
    from ovito.io import import_file
    from ovito.vis import TachyonRenderer, Viewport
    from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication, QImage, QPainter
    application = QGuiApplication.instance() or QGuiApplication([])
    from matplotlib import get_data_path
    font_id = QFontDatabase.addApplicationFont(str(Path(get_data_path()) / 'fonts/ttf/DejaVuSans.ttf'))
    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        raise ValueError('Could not load the portable annotation font.')
    validate_order(type_order)
    integer(width, 'width', 100)
    integer(height, 'height', 100)
    if width > 4000 or height > 4000:
        raise ValueError('Preview dimensions exceed the supported local image budget.')
    if file_format not in {'extxyz', 'lammps-data'}:
        raise ValueError('Preview adapter supports extxyz and atomic LAMMPS data.')
    pipeline = import_file(str(source), **({'atom_style': 'atomic'} if file_format == 'lammps-data' else {}))
    data = pipeline.compute(0)
    if file_format == 'lammps-data':
        for particle_type in data.particles.particle_types.types:
            if particle_type.id < 1 or particle_type.id > len(type_order):
                raise ValueError('Preview numeric type lies outside the explicit mapping.')
        from ovito.modifiers import PythonModifier
        def map_names(frame, dataset):
            types = dataset.particles_.particle_types_
            for particle_type in types.types:
                types.type_by_id_(particle_type.id).name = type_order[particle_type.id - 1]
        pipeline.modifiers.append(PythonModifier(function=map_names))
    output = new_directory(output)
    pipeline.add_to_scene()
    try:
        viewport = Viewport(type=Viewport.Type.Perspective, camera_dir=(-1.0, -1.0, -0.65))
        viewport.zoom_all(size=(width, height))
        rendered = viewport.render_image(size=(width, height), background=(1, 1, 1), renderer=TachyonRenderer(shadows=True))
        # Add an explicit annotation band to the generated scientific figure.
        canvas = QImage(width, height + 52, QImage.Format.Format_RGB32)
        canvas.fill(QColor('white'))
        painter = QPainter(canvas)
        painter.drawImage(0, 52, rendered)
        painter.setPen(QColor('#183047'))
        font = QFont(families[0])
        font.setPixelSize(22)
        painter.setFont(font)
        painter.drawText(18, 34, label)
        painter.end()
        if not canvas.save(str(output / 'structure-preview.png')):
            raise ValueError('Preview image could not be saved.')
    finally:
        pipeline.remove_from_scene()
    report = {'rendered_utc': utc_now(), 'source': identity(source), 'source_frame': 0,
              'renderer': 'OVITO Tachyon software renderer', 'label': label, 'atom_count': data.particles.count,
              'type_order': type_order, 'image': identity(output / 'structure-preview.png'),
              'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False,
              'scope': 'Image preview only; not desktop-GUI, physical geometry or numerical validation.'}
    json_file(output / 'render.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--structure', required=True)
    parser.add_argument('--format', choices=['extxyz', 'lammps-data'], required=True)
    parser.add_argument('--type-order', nargs='+', required=True)
    parser.add_argument('--label', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    report = render(Path(args.structure).resolve(strict=True), args.format, args.type_order, args.output_directory, args.label)
    print_receipt(args.output_directory, atom_count=report['atom_count'], renderer=report['renderer'])


if __name__ == '__main__':
    main()
