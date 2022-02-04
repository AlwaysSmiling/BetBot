import discord
from discord.ext import commands, tasks
import pymongo
import requests

class BettingManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        try:
            client = pymongo.MongoClient()
        except:
            print("MongoDB Client unable to connect. please try again.")
            exit()
        print("MongoDB Client Connected!")
        self.db = client['bettingbot']
        self.bettingchannelid = 928534924703723530

    def createembed(self, dict):
        mes = f"**{dict['title']}** \n"
        nom = 1
        for option in dict['options']:
            mes += f"Option '{nom}': **{option}** \n"
            nom += 1 
        if dict['result'] == 'NA':
            mes += f"Status: **{dict['status']}** \n You can use BetId **{dict['betid']}** to place bets."
        else:
            mes += f"Status: **{dict['status']}** \n Result: **{dict['result']}** \n BetId: **{dict['betid']}**"
        return mes

    def userXp(self, userid=None, rank=None):
        leader = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/600343535711027242?page=0")
        if leader.status_code == 200:
            players = leader.json()['players']
            if rank:
                for i, player in enumerate(players):
                    if i+1 == int(rank):
                        return player['xp']
                leader = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/600343535711027242?page=1")
                if leader.status_code == 200:
                    players = leader.json()['players']
                    for i, player in enumerate(players):
                        if i-101 == int(rank):
                            return player['xp']
            elif userid:
                for player in players:
                    if player['id'] == str(userid):
                        return player['xp']
                leader = requests.get("https://mee6.xyz/api/plugins/levels/leaderboard/600343535711027242?page=1")
                if leader.status_code == 200:
                    players = leader.json()['players']
                    for player in players:
                        if player['id'] == str(userid):
                            return player['xp']
        else:
            return -1

    @commands.command(name="SetBetChannel", aliases=["sbc"], hidden=True)
    @commands.is_owner()
    async def setbettingchannel(self, ctx, channelid):
        '''A betMaster can set the default betting channel for publish bets and results.'''
        self.bettingchannelid = int(channelid)
        await ctx.send(f"Successfully Set betting Channel to <#{self.bettingchannelid}>.")

    @commands.command(name="Setbet", aliases=["sb"], hidden=True)
    @commands.is_owner()
    async def setbet(self, ctx, *pos):
        '''A BetMaster can set bets using this command. the format is:
        [prefix]setbet "[title]" "[unique betid]" "[options 1, 2, 3...]"
        the bot will reply with the betid on successful creation. Do not add a/b/c when setting options. they are handled by the bot.'''
        bet = {'title': pos[0], 'status': 'inactive', 'betid': pos[1].lower(), 'options': pos[2:], 'result': 'NA'}
        bets = self.db['bets']
        pools = self.db['pools']
        betinsert = bets.insert_one(bet)
        poolinsert = pools.insert_one({'betid': pos[1].lower(), 'users': [('User Id', 'User Name', 'Betting Amount', 'Betting Choice')]})
        if betinsert.acknowledged and poolinsert.acknowledged:
            print(f"Successfully created bet. betid={pos[1].lower()}")
            await ctx.send(f'Bet Setup Successful. Bet ID is {pos[1].lower()}')
        else:
            print(f"something went wrong. betid {pos[1].lower()} setup failed.")
            await ctx.send("Bet Setup Failed! Contact a certain Smiling Person.")

    @commands.command(name="ViewBet", aliases=["vb"], hidden=True)
    @commands.is_owner()
    async def viewbet(self, ctx, betid):
        '''A betMaster can view a bet using the provided betid.
        [prefix]viewbet [betid]'''
        bet = self.db.bets.find_one({'betid': betid.lower()})
        await ctx.send(self.createembed(bet))
        

    @commands.command(name="PublishBet", aliases=["pb"], hidden=True)
    @commands.is_owner()
    async def publishbet(self, ctx, betid):
        '''A BetMaster can publish a bet to the public channel using this command.
        [prefix]publishbet [betid]'''
        statup = self.db.bets.update_one({'betid': betid.lower()}, {'$set': {'status': 'active'}})
        if statup.matched_count == statup.modified_count == 1:
            print(f"Bet {betid.lower()} has been set to active.")
            bet = self.db.bets.find_one({'betid': betid.lower()})
            mess = self.createembed(bet) + "\n\n *When placing bets, enter choice as [1/2/3/4...]*."
            await ctx.guild.get_channel(self.bettingchannelid).send(mess)
        else:
            print(f"A Problem occured while setting bet {betid.lower()} to active.")
            await ctx.send("Problem Occured! Please contact a certain Smiling Person.")


    @commands.command(name="CheckPool", aliases=["cp"], hidden=True)
    @commands.is_owner()
    async def checkpool(self, ctx, betid):
        '''A Betmaster can check the current pool for a bet using this command with betid.
        [prefix]checkpool [betid]'''
        pool = self.db.pools.find_one({'betid': betid.lower()})
        mes = "**Bet Id**: **"+pool['betid']+"** \n"
        for user in pool['users']:
            mes += "**" + user[1] + "** \t **" + str(user[2]) + "** \t **" + str(user[3]) + "** \n"
        await ctx.send(mes)

    @commands.command(name="ConcludeBet", aliases=["cb"], hidden=True)
    @commands.is_owner()
    async def concludebet(self, ctx, *det):
        '''A Betmaster can conclude a bet using this command with betid and result.
        [prefix]concludebet [betid] [1/2/3/4....]. This will show the winners and their winnings.'''
        betid = det[0].lower()
        ans = list(map(int, det[1:]))
        bet = self.db.bets.find_one({'betid': betid})
        nom = len(bet['options'])
        if bet['status'] != 'active':
            await ctx.send(f"Invalid BetID, this bet is {bet['status']}.")
        elif min(ans) < 1 or max(ans) > nom+1:
            await ctx.send(f"Invalid Results Choice. Please choose between 1 and {nom}.")
        else:
            pool = self.db.pools.find_one({'betid': betid})
            betsplaced = pool['users'][1:]
            totalxp = 0
            for betplaced in betsplaced:
                totalxp += betplaced[2]
            anspool = []
            for answer in ans:
                ansp = 0
                for betplaced in betsplaced:
                    if betplaced[3] == answer:
                        ansp += betplaced[2]
                anspool.append(ansp)

            totalwinpool = sum(anspool)
            totalwinxp = []
            for ansp in anspool:
                twx = (ansp/totalwinpool)*totalxp
                totalwinxp.append(twx)
            
            users = []
            for i, answer in enumerate(ans):
                for betplaced in betsplaced:
                    if betplaced[3] == answer:
                        reward = int(betplaced[2]*totalwinxp[i]/anspool[i])
                        users.append((betplaced[0], reward))
            
            mes = "Bet **" + betid + "** has concluded. Congratulations to those who won. This bet will not allow anymore entries. \n"
            for user in users:
                mes += "<@" + user[0] + "> has won *" + str(user[1]) + "* XP. \n"
            statup = self.db.bets.update_one({'betid': betid}, {'$set': {'status': 'complete', 'result': ans}})
            if statup.matched_count == statup.modified_count == 1: 
                print(f"{betid} successfully completed.")
                await ctx.guild.get_channel(self.bettingchannelid).send(mes)
            else:
                print(f"{betid} was not successfully completed. some error here.")
                await ctx.send("Some error occured!")
        

    @commands.command(name="DistributeRewards", aliases=["dbr"], hidden=True)
    @commands.is_owner()
    async def distributerewards(self, ctx, betid):
        '''A Betmaster can distribute rewards for a bet using this command with betid.
        [prefix]distributerewards [betid].'''
        bet = self.db.bets.find_one({'betid': betid})
        pool = self.db.pools.find_one({'betid': betid})
        if bet['status'] != 'complete':
            await ctx.send(f"Invalid BetID. This bet is still {bet['status']}")
        else:
            ans = bet['result']
            betsplaced = pool['users'][1:]
            totalxp = 0
            for betplaced in betsplaced:
                totalxp += betplaced[2]
            anspool = []
            for answer in ans:
                ansp = 0
                for betplaced in betsplaced:
                    if betplaced[3] == answer:
                        ansp += betplaced[2]
                anspool.append(ansp)

            totalwinpool = sum(anspool)
            totalwinxp = []
            for ansp in anspool:
                twx = (ansp/totalwinpool)*totalxp
                totalwinxp.append(twx)
            
            giveusers = []
            for i, answer in enumerate(ans):
                for betplaced in betsplaced:
                    if betplaced[3] == answer:
                        reward = int(betplaced[2]*totalwinxp[i]/anspool[i])
                        giveusers.append((betplaced[0], reward - betplaced[2]))
            punishusers = []
            for betplaced in betsplaced:
                if betplaced[3] in ans:
                    continue
                else:
                    punishusers.append((betplaced[0], betplaced[2]))
            mes = "Give-Xp Users: \n"
            for user in giveusers:
                mes += "!give-xp <"+str(user[0])+"> "+str(user[1])+" \n"
            mes += "Remove-Xp Users: \n"
            for user in punishusers:
                mes += "!remove-xp <"+str(user[0])+"> "+str(user[1])+" \n"
            await ctx.send(mes)

    @commands.command(name="UserXP", aliases=["ux"])
    async def userXpcommand(self, ctx, *args):
        '''A Better can check their current xp using this command.
        [prefix]UserXP [optional user mention.]'''
        if len(ctx.message.raw_mentions) == 0:
            if len(args) == 1:
                await ctx.send(f"The Current total xp that user ranked {args[0]} has is {self.userXp(rank=args[0])}.")
            else:
                await ctx.send(f"The Current total xp that <@{ctx.author.id}> has is {self.userXp(userid=ctx.author.id)}.")
        else:
            for mention in ctx.message.raw_mentions:
                await ctx.send(f"The Current total xp that <@{mention}> has is {self.userXp(userid=mention)}.")

    @commands.command(name="Bet", aliases=["bet", "b"])
    async def bet(self, ctx, *details):
        '''A Better can place a bet using this command with betid in the following format.
        [prefix]bet [betid] [amount] [choice]. depending on your level and choice. a bet will be placed.'''
        betid = details[0].lower()
        amount = int(details[1])
        choice = int(details[2])
        userxp = self.userXp(userid=ctx.author.id)
        #check bet validity
        bet = self.db.bets.find_one({'betid': betid})
        nom = len(bet['options'])
        if bet['status'] != 'active':
            await ctx.send("Bet Denied. Invalid BetId.")
        elif choice not in range(1, nom+1):
            await ctx.send("Bet Denied. Invalid Bet Option.")
        elif amount < 1:
            await ctx.send("Bet Denied. Invalid Amount of Xp Betted.")
        elif userxp == -1:
            await ctx.send("Sorry! Error occured while fetching your xp. please try again after some time.")
        elif amount > userxp:
            await ctx.send("Bet Denied. You do not have enough xp.")
        else:
            #add to pool
            pool = self.db.pools.find_one({'betid': betid})
            poolusers = pool['users']
            alreadybetted = False
            for pooluser in poolusers:
                if str(ctx.author.id) == pooluser[0]:
                    alreadybetted = True
                    break
            if alreadybetted: await ctx.send("Bet Denied. You have already Betted.")
            else:
                poolusers.append((str(ctx.author.id), ctx.author.name, amount, choice))
                pools = self.db.pools.update_one({'betid': betid}, {'$set': {'users' :poolusers}})
                if pools.matched_count == pools.modified_count == 1:
                    await ctx.send("Bet Successfully Made")
                else:
                    await ctx.send("Failed to make bet. please contact BetMaster.")

activityofbot = discord.Game(name=" poker with Smile, Noel, and Eve.")
bot = commands.Bot(command_prefix=commands.when_mentioned_or(';;'), activity=activityofbot)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('-------------------')

bot.add_cog(BettingManager(bot))

bot.run('TOKEN')
