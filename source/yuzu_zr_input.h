#ifndef YUZU_ZR_INPUT_H
#define YUZU_ZR_INPUT_H

/* MT Framework's pad bits after native Switch input mapping. */
enum { YUZU_PAD_R = 0x200, YUZU_PAD_ZL = 0x400, YUZU_PAD_ZR = 0x800,
       YUZU_PAD_AX = 0x3000, YUZU_PAD_WEAPON = 0xfa00 };

typedef struct {
    unsigned held, pending, blocked;
} YuzuTrigger;

/* Sample RT before stripping it from the pad. A press used with LT stays
 * blocked even if LT goes up first. The player input path claims lone presses. */
static inline void yuzu_trigger_sample(YuzuTrigger *trigger, unsigned bits)
{
    if (!(bits & YUZU_PAD_ZR)) {
        *trigger = (YuzuTrigger){0};
        return;
    }
    if (!trigger->held) trigger->pending = 1;
    trigger->held = 1;
    if (bits & YUZU_PAD_ZL) trigger->blocked = 1;
    if ((bits & 0xffffu) != YUZU_PAD_ZR) trigger->pending = 0;
}

static inline unsigned yuzu_trigger_take(YuzuTrigger *trigger)
{
    unsigned pending = trigger->pending;
    trigger->pending = 0;
    return pending;
}

static inline unsigned yuzu_ground_spirit_draw_pose(unsigned state,unsigned action,unsigned airborne)
{
    return !airborne&&(state==1||state==2)&&action<=5;
}

static inline unsigned yuzu_aerial_spirit_draw_pose(unsigned state,unsigned airborne)
{
    return airborne&&(state==1||state==2||state==4);
}

static inline unsigned yuzu_aerial_spirit_input(unsigned bits,const YuzuTrigger *trigger,unsigned eligible)
{
    if(eligible&&trigger->pending&&!trigger->blocked&&(bits&0xffffu)==YUZU_PAD_ZR)
        return bits|YUZU_PAD_AX;
    return bits;
}

static inline unsigned yuzu_native_spirit_draw(unsigned action)
{
    return action==20||action==21||(action>=42&&action<=47)||
           (action>=76&&action<=81)||(action>=148&&action<=153);
}

/* Leave the native Hunter Art chord intact. The mod spends any weapon
 * buttons held with LT until their physical release, in either release order. */
static inline unsigned yuzu_weapon_input(unsigned bits, unsigned *spent)
{
    *spent &= bits;
    if (bits & YUZU_PAD_ZL) *spent |= bits & YUZU_PAD_WEAPON;
    return bits & ~*spent;
}

/* GU's actor input uses a different button layout from the pad packet.
 * Keep the stock Type 2 Art command and present Xbox X as its original
 * Switch A input only while LT owns the face buttons. */
enum { GU_ACTOR_Y = 0x10, GU_ACTOR_X = 0x20, GU_ACTOR_B = 0x80,
       GU_ACTOR_A = 0x100, GU_ACTOR_ZL = 0x200,
       GU_ACTOR_FACE = GU_ACTOR_Y | GU_ACTOR_X | GU_ACTOR_B | GU_ACTOR_A };

static inline unsigned yuzu_type2_art_input(unsigned bits, unsigned lt, unsigned spent)
{
    if (!lt) return bits & ~spent;
    unsigned buttons = bits & ~(GU_ACTOR_Y | GU_ACTOR_A);
    if (bits & GU_ACTOR_Y) buttons |= GU_ACTOR_A;
    return buttons;
}

static inline unsigned yuzu_zr_input(unsigned bits, unsigned supported, unsigned drawn)
{
    const unsigned spirit_draw = (bits & YUZU_PAD_AX) == YUZU_PAD_AX;
    const unsigned trigger = bits & YUZU_PAD_ZR;
    if (supported && (drawn || spirit_draw)) {
        bits &= ~YUZU_PAD_R;
        if (trigger && !(bits & YUZU_PAD_ZL)) bits |= YUZU_PAD_R;
    }
    return bits & ~YUZU_PAD_ZR;
}

#endif
