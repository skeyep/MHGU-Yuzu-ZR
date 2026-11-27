/* Run against the release controller and timer hook. GU memory and the native
 * timer callback are fixtures; only a quest can check the native call order. */
#define main controller_suite
#include "test_wilds_controller.c"
#undef main
#include <stdint.h>
typedef uintptr_t uptr;
typedef uint32_t u32;
enum {AREA=4,HP=8,STATE=12,ACTION=16,MOTION=20,RED_AURA_MAX=2700};
#define word(a,n) (*(unsigned *)((char *)(a)+(n)))
#define byte(a,n) (*(unsigned char *)((char *)(a)+(n)))
#define u16(a,n) (*(uint16_t *)((char *)(a)+(n)))
#define real(a,n) (*(float *)((char *)(a)+(n)))
#define put(a,n,v) (word(a,n)=(v))
static WState world;
static unsigned world_bound,world_bound_actor,local,contact;
static float world_regen,world_helm_regen,red_aura_hold,dt;
static unsigned local_supported(void *a){(void)a;return local;}
static unsigned world_contact(void *a){(void)a;return contact;}
#include "shipping_timer.inc"
static void native_tick(void *a){
    if(word(a,0x3330)==3&&real(a,0x332c)>0){
        real(a,0x332c)-=dt;
        if(real(a,0x332c)<=0)word(a,0x3330)=2;
    }
}
static void timers(void){
    unsigned memory[0x3400/4]={0};void *a=memory;
    world_original_timers=native_tick;
    for(unsigned move=W_THRUST;move<=W_LAND;move++)
    for(unsigned variant=0;variant<13;variant++){
        world=(WState){.actor=(u32)(uptr)a,.epoch=1,.move=move,.slot=31,.wilds_helm_red=1,.helm_cost_pending=1};
        helm_guard_actor=world_bound_actor=world.actor;helm_guard_epoch=1;
        helm_guard_ticks=600;world_bound=1;local=contact=1;dt=1;
        byte(a,AREA)=1;u16(a,HP)=100;u16(a,STATE)=16;u16(a,ACTION)=w_action(move);u16(a,MOTION)=0x51f;
        word(a,0x3330)=3;real(a,0x332c)=1;
        switch(variant){
        case 1:world.actor++;break;case 2:byte(a,AREA)++;break;
        case 3:u16(a,HP)=0;break;case 4:u16(a,MOTION)++;break;
        case 5:u16(a,ACTION)++;break;case 6:local=0;break;
        case 7:contact=world.wilds_helm_red=0;break;case 8:helm_guard_ticks=0;break;
        case 9:word(a,0x3330)=4;break;case 10:dt=0;break;
        case 11:world.helm_cost_pending=0;break;case 12:world.move=W_NONE;break;
        }
        world_timers(a);
        if(variant==9)assert(word(a,0x3330)==4);
        else if(variant==0||variant==10||(variant==11&&move!=W_LAND)){
            assert(word(a,0x3330)==3&&real(a,0x332c)==1);
            assert(helm_guard_ticks==600-dt);
        }else assert(word(a,0x3330)==2);
    }
    world.move=W_RISE;u16(a,ACTION)=w_action(W_RISE);
    world.wilds_helm_red=1;word(a,0x3330)=3;real(a,0x332c)=1;helm_guard_ticks=600;
    for(unsigned i=0;i<600;i++)world_timers(a);
    assert(word(a,0x3330)==3&&helm_guard_ticks==0);world_timers(a);assert(word(a,0x3330)==2);
}
static void execution_rank(void){
    CounterRoute routes[]={{0,0,67,0x5ba,2,106,110},{0,0,30,0x57f,1,58,62},
      {W_GROUND,109,0,0,0,46,50},{W_CHARGE,917,0,0,0,51,55},{W_CHARGE,930,0,0,0,39,69}};
    for(unsigned i=0;i<5;i++)for(unsigned initial=0;initial<4;initial++)for(unsigned end=0;end<4;end++){
        WState s;WObservation o;CounterRoute r=routes[i];counter_setup(&s,&o,r);
        for(unsigned f=r.pre;f<=r.execute;f++){
            o.rank=f<r.execute?initial:end;
            WDecision d=counter_sample(&s,&o,f==r.pre?(ML_R|ML_A):0,f);
            if(f==r.execute&&end==3)assert(d.move==W_FORESIGHT&&d.source==918);
            else assert(d.kind==W_KEEP);
        }
    }
}
static void promoted_on_hit(void){
    CounterRoute routes[]={{W_CHARGE,917,0,0,0,51,55},{W_CHARGE,930,0,0,0,39,69}};
    for(unsigned i=0;i<2;i++)for(unsigned hit=0;hit<2;hit++){
        WState s;WObservation o;CounterRoute r=routes[i];counter_setup(&s,&o,r);o.rank=2;
        for(unsigned f=r.pre;f<=r.execute;f++){
            o.contact=(f==r.execute)&&hit;
            WDecision d=counter_sample(&s,&o,f==r.pre?(ML_R|ML_A):0,f);
            if(f==r.execute&&hit)assert(d.move==W_FORESIGHT&&d.source==918&&d.rank_delta==1);
            else assert(d.kind==W_KEEP&&d.rank_delta==0);
        }
    }
}
static void cost(void){
    for(unsigned stage=W_RISE;stage<=W_LAND;stage++){
        WObservation o=obs();WState s={.actor=1,.epoch=1};
        enter(&s,&o,W_THRUST,0);enter(&s,&o,W_RISE,0);
        for(unsigned m=W_AIR;m<=stage;m++)enter(&s,&o,m,0);
        assert(w_leave(&s).rank_delta==(stage>=W_DOWN?-1:0));
        assert(w_leave(&s).rank_delta==0);
    }
    WObservation o=obs();WState s={.actor=1,.epoch=1};
    enter(&s,&o,W_THRUST,0);enter(&s,&o,W_RISE,0);enter(&s,&o,W_AIR,0);
    enter(&s,&o,W_DOWN,0);enter(&s,&o,W_LAND,0);o.base.native_action=w_action(W_LAND);o.base.motion=0x500+s.slot;
    int paid=0;
    for(unsigned f=0;f<45;f++){WDecision d=counter_sample(&s,&o,0,f);paid+=d.rank_delta;o.rank+=d.rank_delta;}
    assert(paid==-1&&o.rank==2&&!s.helm_cost_pending&&w_leave(&s).rank_delta==0);
}
int main(void){timers();execution_rank();promoted_on_hit();cost();puts("PASS: 65 timer cases, watchdog, 80 rank transitions, 4 same-frame hit/whiff cases, 5 cost paths");return 0;}
