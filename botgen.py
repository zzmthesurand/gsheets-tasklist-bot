from cgi import test
from multiprocessing.dummy.connection import Client
import os
import discord 
import gspread
import asyncio
from discord.ui import Button, View, Select, Modal, TextInput
from discord import app_commands
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta, timedelta, date # for mytime command
import json
import requests





############# GSHEETS INITIALIZATION #############
#region
# loading google worksheet
sa = gspread.service_account()
demoSH = sa.open("OMARI Demo Tasklist")

mapWKS = demoSH.worksheet("Maps")
fightWKS = demoSH.worksheet("Fights")
tilesetWKS = demoSH.worksheet("Tilesets")
cutsceneWKS = demoSH.worksheet("Cutscenes")
namesWS = demoSH.worksheet("DiscordID")

wks = {
    "maps": mapWKS,
    "fights": fightWKS,
    "tilesets": tilesetWKS,
    "cutscenes": cutsceneWKS
}

#endregion

############# DISCORD BOT INITIALIZATION ############# 
#region

# place id as test server id
test_guild = discord.Object(id=testidhere)

### loading discord token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

### updating class client
class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.synced = False #we use this so the bot doesn't sync commands more than once

    async def on_ready(self):
        await self.wait_until_ready()
        if not self.synced: #check if slash commands have been synced 
            await tree.sync(guild = test_guild) #guild specific: leave blank if global (global registration can take 1-24 hours)
            self.synced = True
            # tree.clear_commands(guild=None)
            # tree.clear_commands(guild = test_guild)
            # await tree.sync()
            # await tree.sync(guild = test_guild)
        print(f"We have logged in as {self.user}.")
        



### set intents
intents = discord.Intents.default()
intents.message_content = True

### start client and command tree
client = Client()
tree = app_commands.CommandTree(client)


#endregion

############# METHOD INITIALIZATION #############
#region

def mytimeFunc(time:str, currenttime:str, day: int = 0, month: int = 0, year: int = 0, timeremaining: bool = False, label: str = ""):
    """Converts a time string into a discord timestamp."""

    ### VARIABLE INITIALIZATION
    # UTC Offsets
    offsets = [-11, -10, -9.5, -9, -8, -7, -6, -5, -4, -3, -2.5, -2, 1, 0, 1, 2, 3, 4, 4.5, 5, 5.5, 5.75, 6, 6.5, 7, 8, 8.75, 9, 9.5, 10, 10.5, 11, 12]
    # array for the time differences from current time
    timediffer = []
    # the time you want to convert
    wanted = datetime.strptime(time.replace(" ",""), "%I:%M%p").time()
    # current time, used to check which timezone the user is in
    current = datetime.strptime(currenttime.replace(" ",""), "%I:%M%p").time()
    # used for later in date picking
    noDate = not month and not day

    ### pick formatter for time tag
    formatter = "F"
    if noDate: formatter = "t"
    if timeremaining: formatter = "R"

    # if no date is given, use today
    if not year: year = datetime.today().year
    if not month: month = datetime.today().month
    if not day: day = datetime.today().day

    ### getting current time in every timezone
    for i in offsets:
        timef = datetime.now(timezone(timedelta(hours=i))).time().replace(microsecond=0, second=0)
        ### appending time differences to list
        timediffer.append(abs(datetime.combine(date.min, current) - datetime.combine(date.min, timef)))

    ### get offset of closest timezone
    offs = offsets[timediffer.index(min(timediffer))] ### get the offset
    currentTZ = timezone(timedelta(hours=offs)) ### get the current timezone from the offset
    newtime = datetime.combine(date(year, month, day), wanted).replace(tzinfo=currentTZ) ### get the new time

    # if no date was provided, and the wanted time is before the current time, then set the date to tomorrow
    if newtime < datetime.now(tz=currentTZ) and noDate: newtime = newtime + timedelta(days=1)
    
    if label: label += ": "
    timetag = label+"<t:"+str(int(newtime.timestamp()))+":"+formatter+">"
    return timetag

def next_avbl_row(worksheet, col):
    """Method for finding next empty row in a specified column."""
    str_list = list(filter(None, worksheet.col_values(col)))        # Get list of non-empty rows
    return str(len(str_list)+1)                                     # Return index of the row after the list

def clamp(val, minval, maxval):
    """Clamp function because python doesn't freaking HAVE ONE."""
    if val < minval: return minval
    if val > maxval: return maxval
    return val


def in_comm_channel():
    """Checks if the interaction is in the set command channel."""
    def predicate(itx: discord.Interaction) -> bool:
        saveFile = open("servers.json", "r")                        # The .json where the servers and their data are located
        channels = json.load(saveFile)
        saveFile.close()
        channelID = int(channels[str(itx.guild_id)])                # Returns channelID from json dict                
        channel = client.get_channel(channelID)
        return itx.channel_id == channel.id
    return app_commands.check(predicate)

def get_server_channel(itx: discord.Interaction):
    """Returns channel where commands are supposed to be sent."""
    saveFile = open("servers.json", "r")
    channels = json.load(saveFile)
    saveFile.close()
    channelID = int(channels[str(itx.guild_id)])
    channel = client.get_channel(channelID)
    return channel

#endregion

############# MODAL INITIALIZATION #############
#region
### Modal for adding tasks
class add_modal(Modal, title = "Add a Task"):

    worksheet = TextInput(label="Which section?", style = discord.TextStyle.short, placeholder = "Maps/Fights/Tilesets/Cutscenes", required = True)

    answer = TextInput(label="What's the task?", style = discord.TextStyle.short, placeholder = "Writing? Drawing? Coding? Pooping? What's got to be done?", required = True)

    person = TextInput(label="Who's in charge?", style = discord.TextStyle.short, placeholder = "Your mom", required = False)

    async def on_submit(self, interaction: discord.Interaction): 
        if self.worksheet.value.lower() in list(wks.keys()):
            selWK = wks[self.worksheet.value.lower()]
            next_row = next_avbl_row(selWK, 1)
            selWK.update(f"A{next_row}:C{next_row}", [[self.answer.value, self.person.value, self.person.value!=""]])
            selWK.update(f"E{next_row}:H{next_row}", [["NOT STARTED"]*4])
            if self.person.value: charge = f"{self.person.value} is in charge."
            else: charge = ""
            await interaction.response.send_message(f"Received! This is for the {self.answer.value} task. {charge}")
        else:
            await interaction.response.send_message(f"The spreadsheet name you entered does not match any known spreadsheet name. The only options are Maps/Fights/Tilesets/Cutscenes.", ephemeral=True)


class time_modal(Modal, title = "Convert your time to HammerTime"):
    """A modal that obtains the time data for converting string time to discord timestamps."""

    current = TextInput(label="What's the time right now?", style = discord.TextStyle.short, placeholder = "12:34 PM", required=True)

    wanted = TextInput(label="What time do you want to convert?", style = discord.TextStyle.short, placeholder="4:20 PM", required=True)

    date = TextInput(label="What's the date? dd/mm/yyyy please!", style = discord.TextStyle.short, placeholder="dd/mm/yyyy", required=False)

    timer = TextInput(label="Time Remaining? (x minutes left...)", style = discord.TextStyle.short, placeholder="Yes/No", required=False)

    label = TextInput(label="What's the label for this time?", style = discord.TextStyle.short, placeholder="Meeting at, Birthday at, Release at, etc.", required=False)

    async def on_submit(self, itx: discord.Interaction) -> None:
        # if no date was provided, then make day/month/year = 0
        if not self.date.value or self.date.value.lower() in ["na", "none", "n/a"]:
            day = month = year = 0
        else: # else, strip date provided and fill in variables
            currDate = datetime.strptime(self.date.value,"%d/%m/%Y")
            day = currDate.day
            month = currDate.month
            year = currDate.year
        if self.timer.value.lower() in ["yes", "y", "yep", "yeah", "ye", "es"]: timerBool = True
        else: timerBool = False
        await itx.response.send_message(mytimeFunc(self.wanted.value,self.current.value, day, month, year, timerBool, self.label.value))


#endregion

############# BUTTON INITIALIZATION #############
#region

class CancelButton(Button):
    def __init__(self, label="Nevermind"):
        super().__init__(label=label, style=discord.ButtonStyle.secondary)

#endregion

############# VARIABLE INITIALIZATION #############
#region

commandChannels = {}
allowedRoles = ["admin", "council", "honorary council"]

#endregion

############# SLASH COMMANDS #############
#region

@app_commands.checks.cooldown(1, 15.0, key=lambda i: (i.guild_id, i.user.id))
@tree.command(name="ping", description="Get bot ping", guild=test_guild)
@in_comm_channel()
async def _ping(interaction: discord.Interaction):
    await interaction.response.send_message(f'Pong! {round(client.latency *1000)}ms', ephemeral=True)
    print(f"Ping is {round(client.latency *1000)}ms")

@app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
@tree.command(name="hello", description="Say hello!", guild=test_guild)
@in_comm_channel()
async def _hello(interaction: discord.Interaction):
    await interaction.response.send_message("Hello!")

@tree.command(name="check", description="Check for shit", guild=test_guild)
@in_comm_channel()
@app_commands.checks.has_any_role(*allowedRoles)
async def check(interaction: discord.Interaction):
    #if any(role.id in rolelist for role in interaction.user.roles):
    # intializing var
    class Checker():
        def __init__(self):
            self.selWK = None
            self.cols = []
            self.notifList = []

    checker = Checker()

    ################# initializing UI
    # normal view
    view = View() 
    confirmButton = Button(label="Yes, I'm sure", style=discord.ButtonStyle.danger)
    cancelButton = CancelButton()
    view.add_item(confirmButton)
    view.add_item(cancelButton)

    # view for no new tasks
    noNotifView = View(timeout=3) 
    noNotifButton = CancelButton("Sorry for bothering you, Ye.")
    noNotifView.add_item(noNotifButton)

    # initialize view for selecting which sheet to check
    selectView = View()
    selectSheet = Select(options=[
        discord.SelectOption(label="Maps", emoji="🗺", description="The map spreadsheet", value="maps"),
        discord.SelectOption(label="Fights", emoji="👊", description="The fight mechanics spreadsheet", value="fights"),
        discord.SelectOption(label="Tilesets", emoji="🗺", description="The tilesets spreadsheet", value="tilesets"),
        discord.SelectOption(label="Cutscenes", emoji="💬", description="The cutscenes spreadsheet", value="cutscenes")
    ])
    selectView.add_item(selectSheet) 

    ########## PROCESS START
    # ask for spreadsheet chooice
    await interaction.response.send_message("Which spreadsheet would you like to access?", view=selectView, ephemeral=True)

    # pick correct spreadsheet based on user choice and retrieve data
    async def selectWhichSheet(interaction):
        checker.selWK = wks[selectSheet.values[0]]
        print("selected ", selectSheet.values[0])
        checker.cols = checker.selWK.get("B1:C")
        # load names and associated IDs
        namesList = namesWS.get()
        names = {}

        # turn names into dictionary
        for i in namesList:
            names[i[0]] = i[1]

        # for each name with new assign == TRUE, add their string to the notif list
        checker.notifList = []
        addedNames = []
        for id in checker.cols:
            if id[1] == 'TRUE' and id[0] not in addedNames:
                checker.notifList.append(f"<@{names[id[0]]}>")
                addedNames.append(id[0])

        # if there is a single person to notify, write PERSON
        if len(checker.notifList) and len(checker.notifList) == 1:
            await interaction.response.edit_message(content=f"{len(checker.notifList)} person will be notified. Are you sure?", view=view)
        # if there are multiple people to notify, write PEOPLE
        elif len(checker.notifList) and len(checker.notifList) > 1:
            await interaction.response.edit_message(content=f"{len(checker.notifList)} people will be notified. Are you sure?", view=view)
        # if there aren't then don't
        else:
            await interaction.response.edit_message(content="No new task assignments have been made.", view = noNotifView)
            #await interaction.message.delete(delay=10)

    # defining button callbacks
    async def confirmNotif(interaction):
        next_row = next_avbl_row(checker.selWK, 1)
        checker.selWK.update(f"C2:C{next_row}", [[False]]*(int(next_row)-1))
        await interaction.response.edit_message(content=f"Notified {len(checker.notifList)} people.", view=None)
        checker.notifList.append(f"You have been assigned tasks. Please check <https://tinyurl.com/OMARIDEMOTASKS> for your tasks. Thanks!")
        await interaction.followup.send('\n'.join(checker.notifList)) # consolidate list into 1 message

    async def cancelNotif(interaction):
        await interaction.response.edit_message(content="Cancelled operation.", view=None)
        

    # assigning button callbacks
    confirmButton.callback = confirmNotif
    cancelButton.callback = cancelNotif
    noNotifButton.callback = cancelNotif
    noNotifView.on_timeout = cancelNotif
    selectSheet.callback = selectWhichSheet

@tree.command(name="clear", description="Clears messages", guild=test_guild)
@in_comm_channel()
@app_commands.checks.has_any_role("admin")
@app_commands.describe(amount = "Amount of messages to clear.")
async def clear(ctx: discord.Interaction, amount: int = 1):
    delmsgs = await ctx.channel.purge(limit=amount)
    if len(delmsgs) > 1:
        await ctx.response.send_message(f"Cleared {len(delmsgs)} messages", ephemeral = True)
    elif len(delmsgs) == 1:
        await ctx.response.send_message(f"Cleared 1 message", ephemeral = True)
    else:
        await ctx.response.send_message("Cleared no messages", ephemeral=True)

@tree.command(name="add", description="Add a task.", guild=test_guild)
@in_comm_channel()
@app_commands.checks.has_any_role(*allowedRoles)
async def add(interaction: discord.Interaction):
    await interaction.response.send_modal(add_modal())

@app_commands.checks.cooldown(1, 60.0, key=lambda i: (i.guild_id, i.user.id))
@tree.command(name="mytasks", description="Check your tasks.", guild=test_guild)
@in_comm_channel()
async def mytasks(itx: discord.Interaction):
    user = itx.user.id # get users id
    names = namesWS.get() # get names from id database
    username = [i for i in names if str(user) == i[1]] # get username if there is a match
    if len(username) < 1: # catches if no there are no ID matches in the database
        await itx.response.send_message("You were not found in the sheets' DiscordID database. Please consult the admins for further info.", ephemeral=True)
        return
    else: username = username[0] # if it's all good, then get the first element of the (username, ID) tuple
    tasks = [] 
    for sheet in list(wks.values()): # make tasks a list of all the tasks in every sheet
        tasks.extend(sheet.get_values("A2:L"))
    mytasks = [i[0] for i in tasks if i[1] == username[0] and int(i[11]) < 12] # if the task has the user's name and is incomplete, then add to the list
    if len(mytasks) > 1:
        message = f"<@{itx.user.id}>, your following tasks are:\n> " + '\n> '.join(mytasks) # join strings together
    else:
        message = f"Sorry, you don't have any tasks at the moment."
    await itx.response.send_message(message, ephemeral=True)

@tree.command(name="mytime", description="Print given time in everyone's local time.", guild=test_guild)
async def mytime(itx: discord.Interaction):
    await itx.response.send_modal(time_modal())

@tree.command(name="nakednika", description="Naked Nika!", guild=test_guild)
@app_commands.checks.cooldown(1, 15.0, key=lambda i: (i.guild_id, i.user.id))
async def nakednika(itx: discord.Interaction):
    await itx.response.send_message(file=discord.File(r"D:\Programming Stuff\Apps\omari bot\nakednika.mp4"))

@tree.command(name="setchannel", description="Set the channel for this bot's commands", guild=test_guild)
@app_commands.checks.has_any_role("admin")
@app_commands.describe(channel="The channel you want this bot to take commands in. (Most commands, at least)")
async def setchannel(itx: discord.Interaction, channel: discord.TextChannel):
    commandChannels[itx.guild_id] = channel.id
    #await itx.response.send_message(commandChannels[itx.channel.name])
    saveFile = open("servers.json", "w")
    json.dump(commandChannels, saveFile)
    saveFile.close()
    await itx.response.send_message(f"Channel set to {channel.name}.")


@tree.command(name="getchannel", description="Gets the current command channel", guild=test_guild)
@app_commands.checks.cooldown(1, 30.0, key=lambda i: (i.guild_id, i.user.id))
async def getchannel(itx: discord.Interaction):
    saveFile = open("servers.json", "r")
    channels = json.load(saveFile)
    saveFile.close()
    channelID = int(channels[str(itx.guild_id)])
    channel = client.get_channel(channelID)
    await itx.response.send_message(f"The current set command channel is <#{channel.id}>")


#endregion

############# ERROR CATCHES #############
#region

@tree.error
async def on_error(itx: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingAnyRole):
        await itx.response.send_message(f"You do not have the permissions to use this command.", ephemeral=True) 
    elif isinstance(error, app_commands.CommandOnCooldown):
        await itx.response.send_message(f"This command is on cooldown. Please wait {int(error.retry_after)} seconds.", ephemeral=True)
    elif isinstance(error, app_commands.CheckFailure):
        await itx.response.send_message(f"Please use this command in the correct channel. The correct channel is <#{get_server_channel(itx).id}>.", ephemeral=True)

#endregion



# req = requests.get("https://discord.com/api/v7/gateway")
# print(req.headers["retry-after"])

client.run(TOKEN)

# exit
exitCode = ""
while exitCode != "YES":
    exitCode = input("Type YES to shutdown the bot.")

input("Epic")