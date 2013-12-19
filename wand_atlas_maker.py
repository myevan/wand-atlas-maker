import glob

from wand.image import Image

class Rect(object):
    @classmethod
    def new_rect_from_size_and_key(cls, size, padding, key):
        return Rect(0, 0, size[0] + padding, size[1] + padding, key)

    def __init__(self, x, y, width, height, key):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.key = key

    def __repr__(self):
        if self.key is None:
            return "Rect(x=%d, y=%d, width=%d, height=%d)" % (self.x, self.y, self.width, self.height)
        else:
            return "Rect(x=%d, y=%d, width=%d, height=%d, key=%s)" % (self.x, self.y, self.width, self.height, self.key)

    @property
    def extent(self):
        return self.width * self.height

class RectPackingError(Exception):
    pass

class RectPacker(object):
    def __init__(self, width, height):
        self.width = width
        self.height = height

    def pack(self, rects):
        """
        https://github.com/doches/AtlasTool/blob/master/AtlasTool.py
        """

        extent_rect_pairs = [(rect.extent, rect) for rect in rects]
        extent_rect_pairs.sort()

        assignment_rect_dict = {}

        available_rects = [Rect(0, 0, self.width, self.height, key=None)]

        while extent_rect_pairs:
            new_extent, new_rect = extent_rect_pairs.pop()

            best_rect = None
            smallest_extent = 0
            for candidate_rect in available_rects:
                if candidate_rect.width >= new_rect.width and candidate_rect.height >= new_rect.height: 
                    candidate_extent = candidate_rect.extent
                    if best_rect is None or candidate_extent < smallest_extent:
                        smallest_extent = candidate_extent
                        best_rect = candidate_rect

            if not best_rect:
                if 0:
                    print "SKIP_RECT:%s CANVAS(%dx%d)" % (repr(new_rect), self.width, self.height)
                    continue
                else:
                    raise RectPackingError("BIG_RECT:%s CANVAS(%dx%d)" % (repr(new_rect), self.width, self.height))
                
            available_rects.remove(best_rect)
            assignment_rect_dict[new_rect.key] = best_rect

            rest_available_rects = [
                Rect(best_rect.x + new_rect.width, 
                     best_rect.y + new_rect.height,
                     best_rect.width - new_rect.width,
                     best_rect.height - new_rect.height,
                     key = None),
                Rect(best_rect.x, 
                     best_rect.y + new_rect.height,
                     new_rect.width,
                     best_rect.height - new_rect.height,
                     key = None),
                Rect(best_rect.x + new_rect.width, 
                     best_rect.y,
                     best_rect.width - new_rect.width,
                     new_rect.height,
                     key = None)]
            
            for rest_available_rect in rest_available_rects:
                available_rects.append(rest_available_rect)

        return assignment_rect_dict


class Sprite(object):
    def __init__(self, img, img_file_path):
        self.img_file_path = img_file_path
        self.trimmed_img = img.clone()
        self.trimmed_img.trim()
        self.original_img_size = img.size

        self.trimmed_base = (0, 0) if self.trimmed_img.size == img.size else self._find_trimmed_base(img, self.trimmed_img)

    def _find_trimmed_base(self, original_img, trimmed_img):
        trimmed_img_width = trimmed_img.width
        trimmed_img_line = trimmed_img[0]

        for y in xrange(original_img.height):
            original_img_line = original_img[y]
            for x in xrange(original_img.width):
                if trimmed_img_line == original_img_line[x:x+trimmed_img_width]:
                    return (x, y)


def gen_sprites_from_file_pattern(img_file_pattern):
    for img_file_path in glob.glob(img_file_pattern):
        with Image(filename=img_file_path) as img:
            yield Sprite(img, img_file_path)

def pack_sprites(sprites, available_canvas_sizes):
    img_dict = dict((sprite.img_file_path, sprite.trimmed_img) for sprite in sprites)

    rects = [Rect.new_rect_from_size_and_key(sprite.trimmed_img.size, key=sprite.img_file_path, padding=2) for sprite in sprites]
    extents = [rect.extent for rect in rects]

    for canvas_width, canvas_height in available_canvas_sizes:
        rect_packer = RectPacker(canvas_width, canvas_height)
        try:
            packed_rects = rect_packer.pack(rects)
        except RectPackingError:
            continue

        canvas = Image(width=canvas_width, height=canvas_height)
        for key, rect in rect_packer.pack(rects).iteritems():
            canvas.composite(img_dict[key], rect.x, rect.y)

        return canvas, packed_rects

    return None, []

if __name__ == '__main__':
    available_canvas_sizes = [(256,256), (512,256), (512,512), (1024,512), (1024,1024), (2048,1024), (1024,2048), (2048,2048)]

    sprites = list(gen_sprites_from_file_pattern("data/*.png"))
    canvas, packed_rects = pack_sprites(sprites, available_canvas_sizes)
    print packed_rects
    if canvas:
        canvas.save(filename='canvas.png')

