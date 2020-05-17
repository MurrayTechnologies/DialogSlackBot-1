import json

import requests


class JiraHandler(object):

    def __init__(self, data):
        self.data = data

    def createJiraIssue(self):
        activeSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/373/sprint?state=active'
        futureSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/373/sprint?state=future'
        transitionurl = 'https://jira.godaddy.com/rest/api/2/issue/{key}/transitions?expand=transitions.fields'
        
      
        #transition to done
        transitionStr = '{"transition": {"id": "31"}}'
        createjira = 'https://jira.godaddy.com/rest/api/2/issue'
        submission = self.data['submission']
        username = self.data['user']['name']

        jiraproj = self.defineTeam(username)
        currentSprint = self.getResults(self.retrieveSprint(username, "active"))
        labels = ['Interruption']
        labels = self.retrieveCategoryLabels(labels)
        #labels = self.retrieveTeamLabels(labels, username)

        desc = submission['description']

        if username == 'ppettong':
            username = 'ppeachthong'

        if currentSprint['values']:
            sprintId = currentSprint['values'][0]['id']
        else:
            futureSprint1 = self.getResults(self.retrieveSprint(username, "future"))
            sprintId = futureSprint1['values'][0]['id']
        
        if jiraproj != "PKISRE":
            x = {
                "fields":
                {
                    "customfield_10004" : self.populateStoryPoints(),
                    "customfield_10007" : sprintId,
                    "project": {"key": jiraproj},
                    "summary": "Interruption: " + submission['summary'],
                    "issuetype": {"id": 8},
                    "labels": labels,
                    "description": desc,
                    "reporter" : {"name" : username},
                    "assignee" : {"name" : username}
                }
            }
        else:
            x = {
                "fields":
                {
                    "customfield_10004" : self.populateStoryPoints(),
                    "project": {"key": jiraproj},
                    "summary": "Interruption: " + submission['summary'],
                    "issuetype": {"id": 8},
                    "labels": labels,
                    "description": desc,
                    "reporter" : {"name" : username},
                    "assignee" : {"name" : username}
                }
            }


        print (json.dumps(x))
        #ll = json.loads(jsonStr)

        response = self.postResponse(createjira, json.dumps(x))
        print (response.content, response.status_code)

        if response.status_code == 201:
            rr = json.loads(response.content)
            #print (rr)

            self.postResponse(transitionurl.format(key=rr['key']), transitionStr)

        return rr['key']

    def populateStoryPoints(self):
        time = int(self.data['submission']['resolution_time'])
        if time == 1:
            return 1

        if time == 4:
            return 2

        if time == 8:
            return 3

        if time == 36:
            return 5

        if time == 72:
            return 8

        return 1
    
    def defineTeam(self, username):
        plat = ['bhodge', 'schang', 'jkramer1', 'mgilhool', 'astokes', 'meljuga', 'achiliveri', 'mmurray']
        sre = ['lcurran', 'jgorz','jdharano', 'ddubovik', 'tgraham', 'glopez', 'dwilliams1']
        client = ['mxpatterson', 'rmartin', 'bfeddern']
        mssl = ['kcrawford', 'ycampo']
        api = ['sdeitte', 'rjasmin', 'ppettong', 'jpogue']
        
        if username in plat:
            return "PKIPLAT"

        if username in client:
            return "PKICLIENT"
        
        if username in api:
            return "PKIAPI"
        
        if username in mssl:
            return "MSSL"
        
         if username in sre:
            return "PKISRE"
        
    def retrieveSprint(self, username, sprintType):
        plat = ['bhodge', 'schang', 'jkramer1', 'mgilhool', 'astokes', 'meljuga', 'achiliveri', 'mmurray']
        sre = ['lcurran', 'jgorz','jdharano', 'ddubovik', 'tgraham', 'glopez', 'dwilliams1']
        client = ['mxpatterson', 'rmartin', 'bfeddern']
        mssl = ['kcrawford', 'ycampo']
        api = ['sdeitte', 'rjasmin', 'ppettong', 'jpogue']
        
        #PKIPLAT
        platactiveSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/5268/sprint?state=' + sprintType
              
        #PKICLIENT
        clientactiveSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/5266/sprint?state=' + sprintType
        
        #PKIAPI
        apiactiveSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/5267/sprint?state=' + sprintType
        
        #PKISRE
        sreactiveSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/5249/sprint?state=' + sprintType
       
        
        #MSSL
        msslactiveSprint = 'https://jira.godaddy.com/rest/agile/1.0/board/5134/sprint?state=' + sprintType
        
        if username in plat:
            return platactiveSprint

        if username in client:
            return clientactiveSprint
        
        if username in api:
            return apiactiveSprint
        
        if username in mssl:
            return msslactiveSprint
        
        if username in sre:
            return None
       
        
    def retrieveCategoryLabels(self, labels):
        submission = self.data['submission']
        if submission['category_1'] != 'None':
            labels.append(submission['category_1'])

        #if submission['category_2'] != 'None':
        #    labels.append(submission['category_2'])

        return labels
    
    def retrieveDoneTransitionId(self,team):
        if username in plat:
            return "31"

        if username in client:
            return "31"
        
        if username in api:
            return "31"
        
        if username in mssl:
            return "31" 

    def retrieveTeamLabels(self, labels, username):
       
        team_experience = ['sdeitte', 'ppettong', 'schang', 'jkramer1', 'mgilhool', 'jdjensen', 'meljuga']
        team_dev_ops = ['lcurran', 'jgorz','jdharano', 'ddubovik', 'tgraham', 'glopez', 'dwilliams1']
        team_integration = ['rjasmin','mxpatterson','jpogue','rmartin', 'achiliveri','jstack', 'bhodge1','astokes']

        if username in team_experience:
            labels.append('TeamPseudocode')

        if username in team_dev_ops:
            labels.append('TeamPhabulous')
        
        if username in team_integration:
            labels.append('TeamPterodactyl')

        return labels

    def getResults(self, url):
        headers = {"Accept": "application/json", "Content-Type": "application/json",
                   "Authorization": "Basic MDJkODQ4NnJ5NWhBOlduNDEjWSViNW18X3Ez"}
        r = requests.get(url, headers=headers)

        return json.loads(r.content)

    def postResponse(self, url, body):
        headers = {"Accept": "application/json", "Content-Type": "application/json",
                   "Authorization": "Basic MDJkODQ4NnJ5NWhBOlduNDEjWSViNW18X3Ez"}
        #print (body)
        r = requests.post(url, headers=headers, data=body)
        #print (r)
        return r
