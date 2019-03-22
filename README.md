# Pensieve

"*One simply siphons the excess thoughts from one's mind, pours them into the basin, and examines them at one's leisure. It becomes easier to spot patterns and links, you understand, when they are in this form.*"</br>
&mdash;**Albus Dumbledore** (Harry Potter and the Goblet of Fire by J. K. Rowling)

![Picture of Pensieve](https://raw.githubusercontent.com/idin/pensieve/master/pictures/pensieve.jpg)

### Pensieve for Data

In [J. K. Rowling](https://en.wikipedia.org/wiki/J._K._Rowling)'s amazing world of magic, 
"*a witch or wizard can **extract** their own or another's memories, **store** them in the [Pensieve](https://en.wikipedia.org/wiki/Magical_objects_in_Harry_Potter#Pensieve), 
and **review** them later. It also **relieves the mind** when it becomes cluttered with information. 
Anyone can **examine** the memories in the Pensieve, which also allows viewers to fully immerse 
themselves in the memories*" [1](https://en.wikipedia.org/wiki/Magical_objects_in_Harry_Potter#Pensieve). 

Dealing with data during data wrangling and model generation in data science is like dealing with memories 
except that there is a lot more of back and forth and iteration when dealing with data. 
You constantly update parameters of your models, improve your data wrangling, 
and make changes to the ways you visualize or store data. 
As with most processes in data science, each step along the way may take a long time to finish
which forces you to avoid rerunning everything from scratch; this approach is very error-prone as some 
of the processes depend on others. To solve this problem I came up with the idea of a *Computation Graph* 
where the nodes represent data objects and the direction of edges indicate the dependency between them. 

After using Pensieve for some time myself, I have found it to be beneficial in several ways:
* Reduces errors in data wrangling and model creation
* Organizes data objects
* Makes data transfer easier
* Makes data processing more coherent 
* Facilitates the reproduction of data and models
* Most importantly **relieves the mind**


## Installation
```bash
pip install pensieve
```

## Usage
```python
from pensieve import Pensieve
pensieve = Pensieve()
```

### Storing a Memory without Precursors
```python
pensieve.store(key='integers', content=list(range(10)))
```

### Storing a Memory with One Precursor
```python
pensieve.store(
    key='odd_integers', precursors=['integers'],
    function=lambda numbers: [x for x in numbers if x%2==1]
)
```

### Storing a Memory with More than One Precursor
```python
pensieve.store(
    key='even_integers', 
    precursors=['integers', 'odd_integers'],
    function=lambda precursors: [
        x for x in precursors['integers'] 
        if x not in precursors['odd_integers']
    ]
)
```


### Retrieving a Memory
```python
pensieve['integers']
# output: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

pensieve['even_integers']
# output: [0, 2, 4, 6, 8]

```


### Changing a Memory
When you change a memory in Pensieve all successors get notified and marked as stale but not updated immediately.
As soon as a successor of a changed memory is needed it will be updated based on its relationship with its 
precursor memories.

```python
# changing one memory affects all successors
pensieve.store(key='integers', content=list(range(16)))
pensieve['integers']
# output: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]

pensieve['even_integers']
# output: [0, 2, 4, 6, 8, 10, 12, 14]
```

### Save and Load
