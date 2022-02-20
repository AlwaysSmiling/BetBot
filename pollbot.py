from discord.ext import commands
import pymongo

class PollBot(commands.Cog):
    def __init__(self, bot) -> None:
        self.bot = bot 
        try:
            client = pymongo.MongoClient()
        except:
            print("MongoDB Client unable to connect. please try again.")
            exit()
        print("MongoDB Client Connected!")
        self.db = client['pollingbot']
        self.pollchannel = 944956770013552670
    
    @commands.command(name="CreatePoll", aliases=["cpo"], hidden=True)
    @commands.is_owner()
    async def createpoll(self, ctx, *args):
        '''A BotMaster can create polls using this command and add choices in it.
        [prefix]createpoll [pollid] [polltitle] [choice1] [choice2] [choice3] [choice4] ...'''
        poll = {'pollid': args[0].lower(), 'polltitle': args[1], 'choices': args[2:]}
        if self.db.polls.find_one({'pollid': args[0].lower()}):
            await ctx.send(f"There's already a poll with the pollid {args[0].lower()}. Please try another id.")
        else:
            insertconfirm = self.db.polls.insert_one(poll)
            if insertconfirm.acknowledged:
                await ctx.send(f"Poll Created Successfully. Poll ID is {args[0].lower()}")
            else:
                await ctx.send(f"There's Something Wrong. I can feel it.")
    
    @commands.command(name="PublishPoll", aliases=["ppo"], hidden=True)
    @commands.is_owner()
    async def publishpoll(self, ctx, pollid):
        '''A BotMaster can publish polls using this command. Published polls will have their data public.
        [prefix]publishpoll [pollid]'''
        poll = self.db.polls.find_one({'pollid':pollid})
        if poll:
            mes = f"Poll ID: **{poll['pollid']}**\nPoll Title: **{poll['polltitle']}**\n"
            for i, choice in enumerate(poll['choices']):
                mes += f"{i+1}. {choice}\n"
            await ctx.send(mes)
        else:
            await ctx.send("Could not find the poll. please check pollid.")
        
    @commands.command(name="UpdatePoll", aliases=["upo"], hidden=True)
    @commands.is_owner()
    async def updatepoll(self, ctx, *args):
        '''A BotMaster can update any poll with more choices at any time using this command.
        [prefix]updatepoll [pollid] add [choicenew1] [choicenew2] [...] remove [oldchoice1] [oldchoice2] [...]'''
        addchoices = []
        removechoice = []
        add, remove = True, True
        pollid = args[0].lower()
        try:
            firstindex = args.index("add") + 1
            for arg in args[firstindex:]:
                if arg == 'remove': break 
                else: addchoices.append(arg)
        except ValueError:
            add = False
            print("Add params not found")
        
        try:
            lastindex = args.index(addchoices[-1]) + 2
            for arg in args[lastindex:]:
                removechoice.append(arg)
        except ValueError: 
            remove = False
            print("Remove params not found.")
        
        choices = self.db.polls.find_one({'pollid':pollid})['choices']
        newchoice = []
        if remove:
            newchoice = [choice for choice in choices if choice not in removechoice]
        if add:
            newchoice.extend(addchoices)
        newchoice = list(set(newchoice))
        updateconfirm = self.db.polls.update_one({'pollid': pollid}, {'$set':{'choices': newchoice}})
        if updateconfirm.matched_count == 1 and updateconfirm.modified_count == 1:
            await ctx.send("Poll Successfully updated.\nPlease Publish Poll Again.")
        else:
            await ctx.send("Something's Wrong. Idk what.")
    
    @commands.command(name="Vote", aliases=["v"])
    async def vote(self, ctx, *args):
        '''A User can vote on polls using this command. You can only have one vote in the whole poll.
        [prefix]vote [pollid] [choice]''' 
        pollchoices = self.db.polls.find_one({'pollid': args[0].lower()})['choices']
        if args[1].isnumeric():
            userentry = {'pollid': args[0].lower(), 'choice':pollchoices[int(args[1])-1], 'userid': ctx.author.id}
            upsertconfirm = self.db.userentries.find_one_and_update({'userid': ctx.author.id, 'pollid': args[0].lower()}, {'$set': userentry}, upsert=True, return_document=pymongo.ReturnDocument.AFTER)
            if upsertconfirm and upsertconfirm['choice'] == pollchoices[int(args[1])-1]:
                await self.updatechannel(ctx, args[0].lower())
                await ctx.send("Your vote has been recorded.")
            else:
                await ctx.send("Sorry there seems to be an issue. Your vote was not recorded.")
        else:
            await ctx.send("You have entered wrong choice value. please enter a number.")

    async def updatechannel(self, ctx, pollid):
        '''This Method updates the polls results in a set pollingchannel every time there's a new vote.'''
        totalpolls = self.db.polls.count_documents({})
        async for message in ctx.guild.get_channel(self.pollchannel).history(limit=totalpolls):
            if message.content.startswith(f"Poll ID: **{pollid}**"):
                await message.delete()
        poll = self.db.polls.find_one({'pollid': pollid})
        mes = f"Poll ID: **{pollid}**\nPoll Title: **{poll['polltitle']}**\n"
        for i, choice in enumerate(poll['choices']):
            votes = self.db.userentries.count_documents({'pollid': pollid, 'choice': choice})
            mes += f"{i+1}. {choice}: **{votes}**\n"
        
        await ctx.guild.get_channel(self.pollchannel).send(mes)
