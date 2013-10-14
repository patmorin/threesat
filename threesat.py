from __future__ import division
import pygame
import math
import os
from random import randrange, shuffle

def gen_3sat(n):
    """Generate an n-variable 3-sat instance"""
    vars = [ i//7 for i in range(7*n)]
    shuffle(vars)
    return [((vars[3*i], randrange(2)), \
             (vars[3*i+1], randrange(2)), \
             (vars[3*i+2], randrange(2))) for i in range(len(vars)//3) ]
        
def clause_satisfied(a, c):
    """Check if the assignment given by a satisfies the clause c"""
    return reduce(lambda a,b: a or b, \
                  [(a[x[0]] + x[1]) % 2 for x in c])
                  
def formula_satisfied(a, f):
    """Check if the assignment give by a satsifies the formula f"""
    return reduce(lambda a,b: a and b, \
                 [clause_satisfied(a, c) for c in f])
                 
def gauge_easiness(f, n):
    """Determine which fraction of the 2^n assignments satisfy f"""
    a = [0]*(n+1)
    count = 0
    for j in xrange(2**n):
        i = 0
        while a[i] == 1:
            a[i] = 0
            i += 1
        a[i] = 1
        count += formula_satisfied(a, f)
    return count / 2**n
                 
def gen_instance(level):
    """Generate a problem of the appropriate level"""
    n = min(7, 3 + level // 3)
    if n < 7:
        timeout = int(15 + 15/(level%3+1))
    else:
        timeout = 30
    f = gen_3sat(n)
    a = [0]*n
    easiness = gauge_easiness(f, n)
    while formula_satisfied(a, f) \
           or easiness == 0 \
           or easiness > max(1/2**n, 1/(level+1)):
        f = gen_3sat(n)
        easiness = gauge_easiness(f, n)
    return (n, a, f, timeout)
        
# Import the android module. If we can't import it, set it to None - this
# lets us test it, and check to see if we want android-specific behavior.
try:
    import android
except ImportError:
    android = None

# Event constant.
TIMEREVENT = pygame.USEREVENT
RESETEVENT = pygame.USEREVENT+1
TIMEOUTEVENT = pygame.USEREVENT+2

# The FPS the game runs at.
FPS = 30

# Color constants.
RED = (255, 0, 0, 255)
GREEN = (0, 255, 0, 255)
LIGHTGREEN = (144, 238, 144, 255)
BROWN = (165, 42, 42, 255)
BLACK = (0, 0, 0, 255)

WON_STATE = 2
PLAYING_STATE = 1
GAMEOVER_STATE = 3

def main():
    pygame.mixer.init()    # is this necessary?
    pygame.mixer.pre_init(44100, -16, 2, 2048)

    pygame.init()

    # Set the screen size.
    size = width, height = 480, 800
    screen = pygame.display.set_mode(size)

    # Map the back button to the escape key.
    if android:
        android.init()
        android.map_key(android.KEYCODE_BACK, pygame.K_ESCAPE)

    # load sounds
    soundtrack = pygame.mixer.Sound(os.path.join('sounds', 'soundtrack.wav'))
    soundtrack.set_volume(0.3)
    soundtrack.play(-1, 0, 2000)
    win_sound = pygame.mixer.Sound(os.path.join('sounds', 'win2.wav'))
    click_sound = pygame.mixer.Sound(os.path.join('sounds', 'plug.wav'))
    lose_sound = pygame.mixer.Sound(os.path.join('sounds', 'lose.wav'))
    gameover_sound = pygame.mixer.Sound(os.path.join('sounds', 'gameover.wav'))
    
    # load our images
    or_img = pygame.image.load(os.path.join('images', 'or.png'))
    or_imgs = [pygame.image.load(os.path.join('images', 'or0.png')), \
               pygame.image.load(os.path.join('images', 'or1.png')) ]
    notr_img = [pygame.image.load(os.path.join('images', 'not0.png')), \
                pygame.image.load(os.path.join('images', 'not1.png')) ]
    notl_img = [pygame.transform.flip(notr_img[i], True, False) \
                for i in range(2)] 
    var_img = [pygame.image.load(os.path.join('images', 'var0.png')), \
               pygame.image.load(os.path.join('images', 'var1.png'))]
    
    # load our font
    fontfile = pygame.font.match_font('gfsneohellenic,sans')
    font = pygame.font.Font(fontfile, 40)
    print fontfile
    if font == None:    # always have a backup plan
        font = pygame.font.SysFont(None, 40)
    font = pygame.font.SysFont(None, 40)

    # Use a timer to control FPS.
    pygame.time.set_timer(TIMEREVENT, 1000 // FPS)

    # Setup colors of the screen.
    bg_color = BLACK
    wire_colors = [BROWN, LIGHTGREEN]

    # Setup some data
    lives = 3
    score = 0
    state = PLAYING_STATE
    n, a, f, timeout = gen_instance(score//500)
    print "Easiness: %f" % gauge_easiness(f, n)
    start_time = pygame.time.get_ticks()
    pygame.time.set_timer(TIMEOUTEVENT, timeout*1000)


    # compute the on-screen locations of the variables            
    bottom_pad = 0
    rect = var_img[0].get_rect()
    horz_gap = (width - n*rect.width)//(n+1)
    var_tl = [( rect.width*i + horz_gap*(i+1), \
                     height-bottom_pad-rect.height) for i in range(n) ]
    var_c = [ (p[0]+rect.width//2, p[1]+rect.height//2) for p in var_tl ]

    # compute the on-screen locations of the clauses
    rows = int(math.ceil(len(f)/(n-1)))
    rect = or_img.get_rect()
    vert_gap = (height-bottom_pad - var_img[0].get_height() - rows*rect.height) \
                // (rows+1)
    clause_c = []
    imgw = var_img[0].get_rect().width
    imgh = var_img[0].get_rect().height
    for i in range(len(f)):
        r = i // (n-1)
        c = i % (n-1)
        clause_c.append(( (horz_gap+imgw)*(c+1) + horz_gap//2,
                   height-bottom_pad-imgh - (vert_gap+rect.height)*(r+1)) )
    clause_tl = [ (p[0]-rect.width//2, p[1]-rect.height//2) \
                    for p in clause_c ] 

    vert_wire_gap = vert_gap // (3*(n-1)+1)
    horz_wire_gap = or_img.get_width()/4

    while True:
        ev = pygame.event.wait()
        # Android-specific:
        if android:
            if android.check_pause():
                android.wait_for_resume()

        # Draw the screen based on the timer.
        if ev.type == TIMEREVENT:
            screen.fill(bg_color)

            # draw the wires
            for i in range(n):
                pygame.draw.line(screen, wire_colors[a[i]], 
                    (var_c[i][0], var_tl[i][1]), (var_c[i][0], 0))
                    
            for i in range(len(f)):
                r = i // (n-1)
                c = i % (n-1)
                y0 = clause_tl[i][1] + or_img.get_rect().height \
                      + vert_wire_gap * (3 * c + 1)
                sf = sorted(f[i], key=lambda x: x[0])
                if sf[2][0] < c+0.5:
                    sig = (0, 1, 2)
                elif sf[0][0] > c + 0.5:
                    sig = (2, 1, 0)
                else:
                    sig = (0, 1, 0)
                for j in range(len(sf)):
                    truth = (a[sf[j][0]] + sf[j][1]) % 2
                    x = clause_c[i][0]+(j-1)*horz_wire_gap
                    y = y0 + + vert_wire_gap*sig[j]
                    pygame.draw.line(screen, wire_colors[truth], 
                                    (var_c[sf[j][0]][0], y), \
                                    (x, y))
                    pygame.draw.line(screen, wire_colors[truth], 
                                    (x, y), \
                                    (x, clause_c[i][1]))
                    if sf[j][1]:
                        if c >= sf[j][0]:
                            img = notr_img[a[sf[j][0]]]
                            rect = img.get_rect()
                            rect = rect.move(var_c[sf[j][0]][0]-1, y-rect.height//2)
                            screen.blit(img, rect)
                        else:
                            img = notl_img[a[sf[j][0]]]
                            rect = img.get_rect()
                            rect = rect.move(var_c[sf[j][0]][0]-rect.width+2, \
                                             y-rect.height//2)
                            screen.blit(img, rect)
                    
            # draw the variables           
            rect = var_img[0].get_rect()
            for i in range(n):
                screen.blit(var_img[a[i]], rect.move(var_tl[i][0], var_tl[i][1]))
          
            # draw the clauses                  
            rect = or_img.get_rect()
            for i in range(len(f)):
                img = or_imgs[clause_satisfied(a, f[i])]
                screen.blit(img, rect.move(clause_tl[i][0], clause_tl[i][1]))

            # draw the time
            if (state == PLAYING_STATE):
                stop_time = pygame.time.get_ticks()
            rect = pygame.Rect(0, 0, width, vert_gap//2)
            screen.fill(LIGHTGREEN, rect)
            rect = rect.inflate(-10, -10)
            screen.fill(BROWN, rect)
            elapsed = (stop_time-start_time) / 1000
            timeleft = max(0, timeout-elapsed)
            text = font.render("%.0f" % timeleft, True, LIGHTGREEN)
            rect = text.get_rect()
            screen.blit(text, rect.move((width-rect.width)//2, 
                        (vert_gap//2-rect.height)//2 ))
            text = font.render("I" * lives, True, LIGHTGREEN)
            rect = text.get_rect()
            screen.blit(text, rect.move(horz_gap//2, 
                        (vert_gap//2-rect.height)//2 ))
            text = font.render("%d" % score, True, LIGHTGREEN)
            rect = text.get_rect()
            screen.blit(text, rect.move(width-horz_gap//2-rect.width, 
                        (vert_gap//2-rect.height)//2 ))
                        
            if state == GAMEOVER_STATE:
                text = font.render("GAME OVER", True, LIGHTGREEN)
                rect = text.get_rect()
                rect = rect.move((width-rect.width)//2, (height-rect.height)//2)
                screen.fill(LIGHTGREEN, rect.inflate(60, 20))
                screen.fill(BLACK, rect.inflate(50, 10))
                screen.blit(text, rect)
                
            
            
            # now display everything
            pygame.display.flip()

        # Use clicks to toggle variables
        elif state == PLAYING_STATE and ev.type == pygame.MOUSEBUTTONDOWN:
            for i in range(n):
                rect = var_img[0].get_rect()
                rect = rect.move(rect.width*i + horz_gap*(i+1), \
                                 height-bottom_pad-rect.height)             
                if rect.collidepoint(ev.pos):
                    # user clicked on variable
                    click_sound.play()
                    a[i] = (a[i] + 1) % 2
                if formula_satisfied(a, f):
                    soundtrack.fadeout(1000)
                    win_sound.play()
                    score += 100
                    state = WON_STATE
                    delay = int(win_sound.get_length()*1000)
                    pygame.time.set_timer(TIMEOUTEVENT, 0)
                    pygame.time.set_timer(RESETEVENT, delay)

        elif state == GAMEOVER_STATE and ev.type == pygame.MOUSEBUTTONDOWN:
            score = 0
            lives = 3
            pygame.event.post(pygame.event.Event(RESETEVENT, dict()))
            
        # User ran out of time
        elif ev.type == TIMEOUTEVENT:
            print "timeout"
            lives -= 1
            soundtrack.fadeout(1000)
            pygame.time.set_timer(TIMEOUTEVENT, 0)
            if lives > 0:
                state = WON_STATE
                lose_sound.play()
                delay = int(lose_sound.get_length() * 1000)
                pygame.time.set_timer(RESETEVENT, delay)
            else:
                state = GAMEOVER_STATE
                gameover_sound.play()
                        
        # Start a new round
        elif ev.type == RESETEVENT:
            soundtrack.play(-1, 0, 2000)
            pygame.time.set_timer(RESETEVENT, 0)
            state = PLAYING_STATE
            n, a, f, timeout = gen_instance(score//300)
            print "Easiness: %f" % gauge_easiness(f, n)
            
            # FIXME: Huge DUP

            # compute the on-screen locations of the variables            
            bottom_pad = 0
            rect = var_img[0].get_rect()
            horz_gap = (width - n*rect.width)//(n+1)
            var_tl = [( rect.width*i + horz_gap*(i+1), \
                             height-bottom_pad-rect.height) for i in range(n) ]
            var_c = [ (p[0]+rect.width//2, p[1]+rect.height//2) for p in var_tl ]

            # compute the on-screen locations of the clauses
            rows = int(math.ceil(len(f)/(n-1)))
            rect = or_img.get_rect()
            vert_gap = (height-bottom_pad - var_img[0].get_height() - rows*rect.height) \
                        // (rows+1)
            clause_c = []
            imgw = var_img[0].get_rect().width
            imgh = var_img[0].get_rect().height
            for i in range(len(f)):
                r = i // (n-1)
                c = i % (n-1)
                clause_c.append(( (horz_gap+imgw)*(c+1) + horz_gap//2,
                           height-bottom_pad-imgh - (vert_gap+rect.height)*(r+1)) )
            clause_tl = [ (p[0]-rect.width//2, p[1]-rect.height//2) \
                            for p in clause_c ] 

            vert_wire_gap = vert_gap // (3*(n-1)+1)
            horz_wire_gap = or_img.get_width()/4
            print "recomputed parameters"

            pygame.time.set_timer(TIMEOUTEVENT, 0)
            pygame.time.set_timer(TIMEOUTEVENT, timeout*1000)
            start_time = pygame.time.get_ticks()



        # When the user hits back, ESCAPE is sent. Handle it and end
        # the game.
        elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
            break

# This isn't run on Android.
if __name__ == "__main__":
    main()
