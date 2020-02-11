import collections
import operator
import heapq
from pack_algo import PackingAlgorithm
from geometry import Point as P
from geometry import HSegment, Rectangle
from waste import WasteManager


class Skyline(PackingAlgorithm):

    """ Class implementing Skyline algorithm as described by
    Jukka Jylanki - A Thousand Ways to Pack the Bin (February 27, 2010)

    _skyline:  stores all the segments at the top of the skyline.
    _waste: Handles all wasted sections.
    """

    def __init__(self, width, height, rot=True, *args, **kwargs):
        """
        _skyline is the list used to store all the skyline segments, each 
        one is a list with the format [x, y, width] where x is the x
        coordinate of the left most point of the segment, y the y coordinate
        of the segment, and width the length of the segment. The initial 
        segment is allways [0, 0, surface_width]
        
        Arguments:
            width (int, float): 
            height (int, float):
            rot (bool): Enable or disable rectangle rotation
        """
        self._waste_management = False
        self.validation_length = None
        self._waste = WasteManager(rot=rot)
        super(Skyline, self).__init__(width, height, rot, merge=False, *args, **kwargs)

    @staticmethod
    def _placement_points_generator(skyline, width):

        """Returns a generator for the x coordinates of all the placement
        points on the skyline for a given rectangle.

        WARNING: In some cases could be duplicated points, but it is faster
        to compute them twice than to remove them.
        
        Arguments:
            skyline (list): Skyline HSegment list
            width (int, float): Rectangle width

        Returns:
            generator
        """ 
        skyline_r = skyline[-1].right
        skyline_l = skyline[0].left

        # Placements using skyline segment left point
        ppointsl = (s.left for s in skyline if s.left+width <= skyline_r)

        # Placements using skyline segment right point
        ppointsr = (s.right-width for s in skyline if s.right-width >= skyline_l)

        # Merge positions
        return heapq.merge(ppointsl, ppointsr)

    def _generate_placements(self, width, height, overhang):

        """
        Generate a list with 

        Arguments:
            height (number): height of rectangle
            width (number): width of rectangle
            overhang (bool) : indicator of overhang permission

        Returns:
            tuple (Rectangle, fitness):
                Rectangle: Rectangle in valid position
                left_skyline: Index for the skyline under the rectangle left edge.
                right_skyline: Index for the skyline under the rectangle right edte.
        """
        skyline = self._skyline

        points = collections.deque()

        left_index = right_index = 0  # Left and right side skyline index
        support_height = skyline[0].top
        support_index = 0 
    
        placements = self._placement_points_generator(skyline, width)
        for p in placements:

            # If Rectangle's right side changed segment, find new support
            if p+width > skyline[right_index].right:
                for right_index in range(right_index+1, len(skyline)):
                    if skyline[right_index].top >= support_height:
                        support_index = right_index
                        support_height = skyline[right_index].top
                    if p+width <= skyline[right_index].right:
                        break
                
            # If left side changed segment.
            if p >= skyline[left_index].right:
                left_index += 1
           
            # Find new support if the previous one was shifted out.
            if support_index < left_index:
                support_index = left_index
                support_height = skyline[left_index].top
                for i in range(left_index, right_index+1):
                    if skyline[i].top >= support_height:
                        support_index = i
                        support_height = skyline[i].top

            # Add point if there is enough room at the top
            if support_height+height <= self.height + int(overhang)*self.overhang_measure and \
                    support_height + int(overhang)*self.SBOT*height <= self.height:
                points.append((Rectangle(p, support_height, width, height), left_index, right_index))

        return points

    @staticmethod
    def _merge_skyline(skylineq, segment):
        """
        Arguments:
            skylineq (collections.deque):
            segment (HSegment):
        """
        if len(skylineq) == 0:
            skylineq.append(segment)
            return

        if skylineq[-1].top == segment.top:
            s = skylineq[-1]
            skylineq[-1] = HSegment(s.start, s.length+segment.length)
        else:
            skylineq.append(segment)

    def _add_skyline(self, rect):

        """
        Arguments:
            rect (Rectangle):
        """

        skylineq = collections.deque([])  # Skyline after adding new one
        
        for sky in self._skyline:
            if sky.right <= rect.left or sky.left >= rect.right:
                self._merge_skyline(skylineq, sky)
                continue

            if sky.left < rect.left < sky.right:

                # Skyline section partially under segment left
                self._merge_skyline(skylineq, HSegment(sky.start, rect.left-sky.left))
                sky = HSegment(P(rect.left, sky.top), sky.right-rect.left)
            
            if sky.left < rect.right:
                if sky.left == rect.left:
                    self._merge_skyline(skylineq, HSegment(P(rect.left, rect.top), rect.width))

                # Skyline section partially under segment right
                if sky.right > rect.right:
                    self._merge_skyline(skylineq, HSegment(P(rect.right, sky.top), sky.right-rect.right))
                    sky = HSegment(sky.start, rect.right-sky.left)
            
            if sky.left >= rect.left and sky.right <= rect.right:

                # Skyline section fully under segment, account for wasted space
                if self._waste_management and sky.top < rect.bottom:
                    self._waste.add_waste(sky.left, sky.top, sky.length, rect.bottom - sky.top)
            else:
                # Segment
                self._merge_skyline(skylineq, sky)

        self._skyline = list(skylineq)

    def _rect_fitness(self, rect, left_index, right_index):
        return rect.top

    def _select_position(self, width, height, overhang):
        """
        Search for the placement with the bes fitness for the rectangle.

        Returns:
            tuple (Rectangle, fitness) - Rectangle placed in the fittest position
            None - Rectangle couldn't be placed
        """
        positions = self._generate_placements(width, height, overhang)
        if self.rot and width != height:
            positions += self._generate_placements(height, width, overhang)
        if not positions:
            return None, None
        return min(((p[0], self._rect_fitness(*p))for p in positions), key=operator.itemgetter(1))

    def fitness(self, width, height, overhang):
        """Search for the best fitness 
        """
        # Compute overhang measure of the surface (Notice that it equals 0 if overhang is false)
        oh = int(overhang)*self.overhang_measure

        # Check if it fits on the surface
        assert(width > 0 and height > 0)
        if width > max(self.width, self.height + oh) or\
            height > max(self.height + oh, self.width) or\
           (overhang and width > max(self.width, self.height/self.SBOT)) or\
           (overhang and height > max(self.height/self.SBOT, self.width)):
            return None

        # If there is room in wasted space, FREE PACKING!!
        if self._waste_management:
            if self._waste.fitness(width, height) is not None:
                return 0

        # Get best fitness segment, for normal rectangle, and for
        # rotated rectangle if rotation is enabled.
        rect, fitness = self._select_position(width, height, overhang)
        return fitness

    def add_rect(self, width, height, rid, overhang):
        """
        Add new rectangle
        """
        # Compute overhang measure of the surface (Notice that it equals 0 if overhang is false)
        oh = int(overhang)*self.overhang_measure

        # Check if it fits on the surface
        assert(width > 0 and height > 0)
        if width > max(self.width, self.height + oh) or\
            height > max(self.height + oh, self.width) or\
            (overhang and width > max(self.width, self.height/self.SBOT)) or\
                (overhang and height > max(self.height/self.SBOT, self.width)):
            return None

        rect = None
        # If Waste management is enabled, first try to place the rectangle there
        if self._waste_management:
            rect = self._waste.add_rect(width, height, rid)

        # Get best possible rectangle position
        if not rect:
            rect, _ = self._select_position(width, height, overhang)
            if rect:
                self._add_skyline(rect)

        if rect is None:
            return None
        
        # Store rectangle, and recalculate skyline
        rect.rid = rid
        self.rectangles.append(rect)
        return rect

    def reset(self):
        super(Skyline, self).reset()
        self._skyline = [HSegment(P(0, 0), self.width)]
        self._waste.reset()


class SkylineWMixin(Skyline):

    """Waste managment mixin"""
    def __init__(self, width, height, *args, **kwargs):
        super(SkylineWMixin, self).__init__(width, height, *args, **kwargs)
        self._waste_management = True


class SkylineMwf(Skyline):
    """Implements Min Waste fit heuristic, minimizing the area wasted under the
    rectangle.
    """
    def _rect_fitness(self, rect, left_index, right_index):
        waste = 0
        for seg in self._skyline[left_index:right_index+1]:
            waste +=\
                (min(rect.right, seg.right)-max(rect.left, seg.left)) *\
                (rect.bottom-seg.top)

        return waste

    def _rect_fitnes2s(self, rect, left_index, right_index):

        waste = ((min(rect.right, seg.right)-max(rect.left, seg.left))
                 for seg in self._skyline[left_index:right_index+1])

        return sum(waste)


class SkylineMwfl(Skyline):
    """Implements Min Waste fit with low profile heuritic, minimizing the area
    wasted below the rectangle, at the same time it tries to keep the height
    minimal.
    """ 
    def _rect_fitness(self, rect, left_index, right_index):
        waste = 0
        for seg in self._skyline[left_index:right_index+1]:
            waste +=\
                (min(rect.right, seg.right)-max(rect.left, seg.left)) *\
                (rect.bottom-seg.top)

        return waste*self.width*self.height+rect.top


class SkylineBl(Skyline):
    """Implements Bottom Left heuristic, the best fit option is that which
    results in which the top side of the rectangle lies at the bottom-most 
    position.
    """
    def _rect_fitness(self, rect, left_index, right_index):
        return rect.top

    def get_validation_length(self, starting_height):
        """
        Computes a validation length of the load (Only valid with bottom left heuristic)
        :return: length (float)
        """
        # We initialize an horizontal segment
        h_segment = HSegment(P(0, starting_height), self.width*0.55)

        # We initialize a variable memorizing if we met another horizontal segment
        intersect = False

        # We slowly decrease segment height until our right edge intersect an other
        while not intersect and h_segment.top > 0:
            for segment in self._skyline:
                if h_segment.right_intersect(segment):
                    intersect = True

            h_segment.start.y -= 0.1
            h_segment.end.y -= 0.1

        self.validation_length = h_segment.top
        return self.validation_length


class SkylineBlWm(SkylineBl, SkylineWMixin):
    pass


class SkylineMwfWm(SkylineMwf, SkylineWMixin):
    pass


class SkylineMwflWm(SkylineMwfl, SkylineWMixin):
    pass
