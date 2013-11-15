from __future__ import division
import pygame
import math
import os
from random import randrange, shuffle


class Formula(object):
    """Represent a 3-CNF SAT formula
    
    The internal representation is a list, f, of 3-tuples of pairs
    f[i][j][0] is the j'th variable in the i'th clause and f[i][j][1]
    is 1 or 0 depending on whether the variable is negated or not""" 
    def __init__(self, n):
        """Generate an n-variable 3-sat instance"""
        vars = [ i//7 for i in range(7*n)]
        shuffle(vars)
        self.n = n
        self.f = [((vars[3*i], randrange(2)), \
                  (vars[3*i+1], randrange(2)), \
                  (vars[3*i+2], randrange(2))) for i in range(len(vars)//3) ]

    def clause_satisfied(self, a, c):
        """Check if the assignment given by a satisfies the clause c"""
        return reduce(lambda a,b: a or b, \
                      [(a[x[0]] + x[1]) % 2 for x in c])
                  
    def formula_satisfied(self, a):
        """Check if the assignment give by a satsifies the formula f"""
        return reduce(lambda a,b: a and b, \
                     [self.clause_satisfied(a, c) for c in self.f])
                 
    def easiness(self):
        """Determine which fraction of the 2^n assignments satisfy f"""
        a = [0]*(self.n+1)
        count = 0
        for j in xrange(2**self.n):
            i = 0
            while a[i] == 1:
                a[i] = 0
                i += 1
            a[i] = 1
            count += self.formula_satisfied(a)
        return count / 2**self.n
        
    def __getitem__(self, i):
        return self.f[i]
        
    def __len__(self):
        return len(self.f)


def gen_instance(level):
    """Generate a problem of the appropriate level"""
    n = min(8, 4 + level // 3)
    if n < 8:
        timeout = int(15 + 15/(level%3+1))
    else:
        timeout = 30
    f = Formula(n)
    a = [0]*n
    easiness = f.easiness()
    while f.formula_satisfied(a) \
           or easiness == 0 \
           or easiness > max(1/2**n, 1/(level+1)):
        f = Formula(n)
        easiness = f.easiness()
    return (n, a, f, timeout)


class GameInfo(object):
    """This class holds basic data about the current game"""
    def __init__(self):
        self.lives = 3
        self.score = 0
        self.state = PLAYING_STATE
        self.new_level()
        
    def new_level(self):
        self.n, self.a, self.f, self.timeout = gen_instance(self.score//300)
        self.start_time = pygame.time.get_ticks()
    
        
# Import the android module. If we can't import it, set it to None - this
# lets us test it, and check to see if we want android-specific behavior.
try:
    import android
except ImportError:
    android = None

# event constants
TIMEREVENT = pygame.USEREVENT
RESETEVENT = pygame.USEREVENT+1
TIMEOUTEVENT = pygame.USEREVENT+2

# aim for 30 frames per second
FPS = 30

# color constants
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
LIGHTGREEN = (144, 238, 144, 255)
BROWN = (165, 42, 42, 255)
BLACK = (0, 0, 0, 255)

# ui/game states
WON_STATE = 2
PLAYING_STATE = 1
GAMEOVER_STATE = 3

def load_image(filename):
    """Load an image from the images directory"""
    return pygame.image.load(os.path.join('images', filename))

class UserInterface(object):
    """This is our game's user interface"""
    def __init__(self, info):
        self.info = info
        pygame.mixer.init()    # is this necessary?
        pygame.mixer.pre_init(44100, -16, 2, 2048)

        pygame.init()

        # Set the screen size.
        size = self.width, self.height = 480, 800
        self.screen = pygame.display.set_mode(size)

        # Map the back button to the escape key.
        if android:
            android.init()
            android.map_key(android.KEYCODE_BACK, pygame.K_ESCAPE)

        # load our sounds
        snddir = 'sounds'
        self.soundtrack \
           = pygame.mixer.Sound(os.path.join(snddir, 'soundtrack.wav'))
        self.soundtrack.set_volume(0.3)
        self.soundtrack.play(-1, 0, 2000)
        self.win_sound \
           = pygame.mixer.Sound(os.path.join(snddir, 'win2.wav'))
        self.click_sound \
           = pygame.mixer.Sound(os.path.join(snddir, 'plug.wav'))
        self.lose_sound \
           = pygame.mixer.Sound(os.path.join(snddir, 'lose.wav'))
        self.gameover_sound \
           = pygame.mixer.Sound(os.path.join(snddir, 'gameover.wav'))

        # load our images
        imgdir = 'images'
        self.or_img = [load_image('or0.png').convert_alpha(), \
                       load_image('or1.png').convert_alpha() ]
        self.notr_img = [load_image('not0.png').convert_alpha(), \
                         load_image('not1.png').convert_alpha() ]
        self.notl_img = [pygame.transform.flip(self.notr_img[i], True, False) \
                         for i in range(2)] 
        self.var_img = [load_image('var0.png').convert_alpha(), \
                        load_image('var1.png').convert_alpha()]

        # load our font
        fontfile = pygame.font.match_font('gfsneohellenic,sans')
        self.font = pygame.font.Font(fontfile, 40)
        if self.font == None:    # always have a backup plan
            self.font = pygame.font.SysFont(None, 40)
        self.font = pygame.font.SysFont(None, 40)

        # pick colors
        self.bg_color = BLACK
        self.wire_colors = [BROWN, LIGHTGREEN]

        # compute on-screen locations of everything
        self.updated_formula()
        
        # start up some timers
        pygame.time.set_timer(TIMEREVENT, 1000 // FPS)
        
    def updated_formula(self):
        """Call this when the formula changes changes"""
        pygame.time.set_timer(TIMEOUTEVENT, self.info.timeout*1000)
        # compute the on-screen locations of the variables            
        n = self.info.n
        m = len(self.info.f)
        ow = self.or_img[0].get_width()
        oh = self.or_img[0].get_height()
        varw = self.var_img[0].get_width()
        varh = self.var_img[0].get_height()
        self.bottom_pad = 0
        self.horz_gap = (self.width - n*ow)//(n+1)
        self.var_tl = [(ow*i + self.horz_gap*(i+1), \
                       self.height-self.bottom_pad-varh) for i in range(n)]
        self.var_c = [(p[0]+ow//2, p[1]+oh//2) for p in self.var_tl ]

        # compute the on-screen locations of the clauses
        self.rows = int(math.ceil(m/(n-1)))
        self.vert_gap = (self.height-self.bottom_pad - varh - oh*self.rows) // (self.rows+1)
        self.clause_c = []
        for i in range(m):
            r = i // (n-1)
            c = i % (n-1)
            self.clause_c.append(( (self.horz_gap+varw)*(c+1) + self.horz_gap//2,
                      self.height-self.bottom_pad-varh - (self.vert_gap+oh)*(r+1)) )
        self.clause_tl = [ (p[0]-ow//2, p[1]-oh//2) for p in self.clause_c ] 

        self.vert_wire_gap = self.vert_gap // (3*(n-1)+1)
        self.horz_wire_gap = ow/4

    def run(self):
        while True:
            
            ev = pygame.event.wait()
            # Android-specific:
            if android:
                if android.check_pause():
                    android.wait_for_resume()

            # Draw the screen based on the timer.
            if ev.type == TIMEREVENT:
                self.draw()

            # Use clicks to toggle variables
            elif self.info.state == PLAYING_STATE \
                 and ev.type == pygame.MOUSEBUTTONDOWN:
                self.clicked(ev.pos)

            # User wants to play again
            elif self.info.state == GAMEOVER_STATE \
                 and ev.type == pygame.MOUSEBUTTONDOWN:
                self.info.__init__()
                pygame.event.post(pygame.event.Event(RESETEVENT, dict()))
                
            # User ran out of time
            elif ev.type == TIMEOUTEVENT:
                self.timeout()
                            
            # Start a new round
            elif ev.type == RESETEVENT:
                self.new_round()

            # When the user hits back, ESCAPE is sent. Handle it and end
            # the game.
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                break

            elif ev.type == pygame.QUIT:
                break

    def new_round(self):
        """Start a new round"""
        self.soundtrack.play(-1, 0, 2000)
        pygame.time.set_timer(RESETEVENT, 0)
        self.info.state = PLAYING_STATE
        self.info.new_level()
        self.updated_formula()
        pygame.time.set_timer(TIMEOUTEVENT, 0)
        pygame.time.set_timer(TIMEOUTEVENT, self.info.timeout*1000)
        self.info.start_time = pygame.time.get_ticks()

    def timeout(self):
        """The user ran out of time for the current puzzle"""
        self.info.lives -= 1
        self.soundtrack.fadeout(1000)
        pygame.time.set_timer(TIMEOUTEVENT, 0)
        if self.info.lives > 0:
            self.info.state = WON_STATE
            self.lose_sound.play()
            delay = int(self.lose_sound.get_length() * 1000)
            pygame.time.set_timer(RESETEVENT, delay)
        else:
            self.info.state = GAMEOVER_STATE
            self.gameover_sound.play()

    def clicked(self, pos):
        """User clicked somewhere---toggle the appropriate variable"""
        for i in range(self.info.n):
            rect = self.var_img[0].get_rect()
            rect = rect.move(self.var_tl[i][0], self.var_tl[i][1])             
            if rect.collidepoint(pos):
                # user clicked on variable
                self.click_sound.play()
                self.info.a[i] = (self.info.a[i] + 1) % 2
                break
        if self.info.f.formula_satisfied(self.info.a):
            self.soundtrack.fadeout(1000)
            self.win_sound.play()
            self.info.score += 100
            self.info.state = WON_STATE
            delay = int(self.win_sound.get_length()*1000)
            pygame.time.set_timer(TIMEOUTEVENT, 0)
            pygame.time.set_timer(RESETEVENT, delay)

    def draw(self):
        """Draw the entire UI"""
        screen = self.screen
        screen.fill(self.bg_color)

        n = self.info.n
        f = self.info.f
        m = len(f)
        a = self.info.a

        # draw the vertical wires leading up from variables
        for i in range(n):
            pygame.draw.line(self.screen, self.wire_colors[a[i]], 
                (self.var_c[i][0], self.var_tl[i][1]), (self.var_c[i][0], 0))
                
        # draw the wires connected to clauses
        for i in range(m):
            r = i // (n-1)
            c = i % (n-1)
            y0 = self.clause_tl[i][1] + self.or_img[0].get_height() \
                  + self.vert_wire_gap * (3 * c + 1)
            # logic to avoid crossings near clauses
            sf = sorted(self.info.f[i], key=lambda x: x[0])
            if sf[2][0] < c+0.5: sig = (0, 1, 2)
            elif sf[0][0] > c + 0.5: sig = (2, 1, 0)
            else: sig = (0, 1, 0)
            for j in range(len(sf)):
                truth = (a[sf[j][0]] + sf[j][1]) % 2
                x = self.clause_c[i][0]+(j-1)*self.horz_wire_gap
                y = y0 + + self.vert_wire_gap*sig[j]
                pygame.draw.line(screen, self.wire_colors[truth], 
                                (self.var_c[sf[j][0]][0], y), \
                                (x, y))
                pygame.draw.line(screen, self.wire_colors[truth], 
                                (x, y), \
                                (x, self.clause_c[i][1]))
                if sf[j][1]:
                    # this variable is negated, draw inverter
                    if c >= sf[j][0]:
                        img = self.notr_img[a[sf[j][0]]]
                        rect = img.get_rect()
                        rect = rect.move(self.var_c[sf[j][0]][0]-1, \
                                         y-rect.height//2)
                    else:
                        img = self.notl_img[a[sf[j][0]]]
                        rect = img.get_rect()
                        rect = rect.move(self.var_c[sf[j][0]][0]-rect.width+2, \
                                         y-rect.height//2)
                    screen.blit(img, rect)
                
        # draw the variables           
        rect = self.var_img[0].get_rect()
        for i in range(n): 
            rect2 = rect.move(self.var_tl[i][0], self.var_tl[i][1])
            screen.blit(self.var_img[a[i]], rect2)
      
        # draw the clauses                  
        rect = self.or_img[0].get_rect()
        for i in range(m):
            rect2 = rect.move(self.clause_tl[i][0], self.clause_tl[i][1])
            img = self.or_img[f.clause_satisfied(a, f[i])]
            screen.blit(img, rect2)

        # draw text elements---lives, time, and score
        rect = pygame.Rect(0, 0, self.width, self.vert_gap//2)
        screen.fill(LIGHTGREEN, rect)
        rect = rect.inflate(-10, -10)
        screen.fill(BROWN, rect)
        if (self.info.state == PLAYING_STATE):
            elapsed = (pygame.time.get_ticks() - self.info.start_time)/1000
            timeleft = max(0, self.info.timeout-elapsed)
            text = self.font.render("%.0f" % timeleft, True, LIGHTGREEN)
            rect = text.get_rect()
            screen.blit(text, rect.move((self.width-rect.width)//2, 
                        (self.vert_gap//2-rect.height)//2 ))
        text = self.font.render("I" * self.info.lives, True, LIGHTGREEN)
        rect = text.get_rect()
        screen.blit(text, rect.move(self.horz_gap//2, 
                    (self.vert_gap//2-rect.height)//2 ))
        text = self.font.render("%d" % self.info.score, True, LIGHTGREEN)
        rect = text.get_rect()
        screen.blit(text, rect.move(self.width-self.horz_gap//2-rect.width, 
                    (self.vert_gap//2-rect.height)//2 ))
                    
        if self.info.state == GAMEOVER_STATE:
            # draw a big game over
            text = self.font.render("GAME OVER", True, LIGHTGREEN)
            rect = text.get_rect()
            rect = rect.move((self.width-rect.width)//2, (self.height-rect.height)//2)
            screen.fill(LIGHTGREEN, rect.inflate(60, 20))
            screen.fill(BLACK, rect.inflate(50, 10))
            screen.blit(text, rect)
        
        # now display everything
        pygame.display.flip()

    
def main():
    """Program entry point"""
    info = GameInfo()    
    ui = UserInterface(info)
    ui.run()



# This isn't run on Android.
if __name__ == "__main__":
    main()
