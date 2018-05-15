#!/usr/bin/env python3
import argparse
import concurrent.futures
import os

import requests
import PIL.Image


CACHE_DIR = os.path.join(os.path.dirname(os.path.realpath(__file__)), '.cache')


class Tile:

    def __init__(self, *, layer, zoom, x, y):
        self.layer = layer
        self.zoom = zoom
        self.x = x
        self.y = y

    @property
    def cache_path(self):
        return os.path.join(CACHE_DIR, self.layer, str(self.zoom), str(self.x), str(self.y))

    def fetch(self):
        r = requests.get(self.url)
        r.raise_for_status()
        cache_dir = os.path.dirname(self.cache_path)
        if not os.path.isdir(cache_dir):
            os.makedirs(cache_dir)
        tmp_path = self.cache_path + '.tmp'
        with open(tmp_path, 'wb') as fh:
            fh.write(r.content)
        os.rename(tmp_path, self.cache_path)

    @property
    def is_cached(self):
        return os.path.exists(self.cache_path)

    @property
    def url(self):
        return 'https://opencache.statkart.no/gatekeeper/gk/gk.open_gmaps?layers={layer}&zoom={zoom}&x={x}&y={y}'.format(
            layer=self.layer,
            zoom=self.zoom,
            x=self.x,
            y=self.y,
        )


def parse_args():
    parser = argparse.ArgumentParser(description='Fetch Statkart map area')
    parser.add_argument('--layer', default='norgeskart_bakgrunn', help='Map layer to fetch')
    parser.add_argument('zoom', type=int)
    parser.add_argument('x_min', type=int)
    parser.add_argument('y_min', type=int)
    parser.add_argument('x_max', type=int)
    parser.add_argument('y_max', type=int)
    return parser.parse_args()


def fetch_missing(tiles):
    tiles_to_fetch = [ tile for tile in tiles if not tile.is_cached ]
    print('Need to fetch {num} tiles'.format(num=len(tiles_to_fetch)))
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        for tile in tiles_to_fetch:
            executor.submit(tile.fetch)
    print('Done')


def main():
    args = parse_args()

    tiles = []
    for y in range(args.y_min, args.y_max + 1):
        for x in range(args.x_min, args.x_max + 1):
            tiles.append(Tile(layer=args.layer, zoom=args.zoom, x=x, y=y))
    fetch_missing(tiles)

    width = (args.x_max - args.x_min + 1) * 256
    height = (args.y_max - args.y_min + 1) * 256
    print('Building {width}x{height} image'.format(width=width, height=height))
    image = PIL.Image.new(mode='RGBA', size=(width, height), color=None)
    for tile in tiles:
        target_x = (tile.x - args.x_min) * 256
        target_y = (tile.y - args.y_min) * 256
        with PIL.Image.open(tile.cache_path) as tile_image:
            image.paste(im=tile_image, box=(target_x, target_y))
    target_name = '{layer}-{zoom}-{x_min}-{y_min}-{x_max}-{y_max}.png'.format(
        layer=args.layer,
        zoom=args.zoom,
        x_min=args.x_min,
        y_min=args.y_min,
        x_max=args.x_max,
        y_max=args.y_max,
    )
    image.save(target_name)
    print('Generated {target_name}'.format(target_name=target_name))


if __name__ == '__main__':
    main()
