# *Pensieve 2.1*

"*One simply siphons the excess thoughts from one's mind, pours them into the basin, and examines them at one's leisure. It becomes easier to spot patterns and links, you understand, when they are in this form.*"</br>
&mdash;**Albus Dumbledore** (Harry Potter and the Goblet of Fire by J. K. Rowling)

![Picture of Pensieve](https://raw.githubusercontent.com/idin/pensieve/master/pictures/pensieve_600.jpg)

### Pensieve for Data

In [J. K. Rowling](https://en.wikipedia.org/wiki/J._K._Rowling)'s words: 
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
* error reduction, especially for data wrangling and model creation
* data object organization
* easy transfer of data
* coherent data processing and data pipelines
* data and model reproducibility
* most importantly **relieving the mind**


## Installation
```bash
pip install pensieve
```

## Usage
Pensieve stores *memories* and *functions* that define the relationship between memories.

```python
from pensieve import Pensieve

# initiate a pensieve
pensieve = Pensieve()

# store a "memory" (with 1 as its content) 
pensieve.store(key='one', content=1)

# create a new memory made up of a precursor memory
pensieve.store(key='two', precursors=['one'], function=lambda x: x + x)
```

There are two types of memories:
- *independent* memories (without precursors)
- *dependent* memories (with precursors)

### Independent Memories
An independent memory does not have any precursors and instead of a function, 
which would define the relationship with the precursors, has *content*.

```python
from pensieve import Pensieve
pensieve = Pensieve()
pensieve.store(key='integers', content=list(range(10)))
```

### Dependent Memories
A dependent memory is created from running a *function* on the contents of 
its *precursors*. When there is only one precursor to a memory, the function can be
defined as a lambda with one input which is accessed directly within the function, 
*e.g.*, *lambda x: x + 1*.

```python
# the precursor, 'integer' is accessed within the lambda under the label: numbers
pensieve.store(
    key='odd_integers', precursors=['integers'],
    function=lambda numbers: [x for x in numbers if x%2==1]
)
```

### Memory with Two or More *Precursors*
If a memory has multiple precursors, its function should still have one input but 
the precursors should be accessed as items in the input, as if the input is a dictionary
of precursors.

For example, if a function adds two precursors *x* and *y*, it should be defined as:
*lambda x: x['x'] + x['y']*. In the following example, the function gets a set of integers and 
odd integers and by filtering out the odd integers from integers, it finds all even integers
in the set. This function has only one input, which is called *precursors* for clarity 
(but can be called anything) and the precursors are accessed within the function as 
items *'integers'* and *'odd_integers'* like a dictionary.

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
Retrieving the content of a memory is like getting an item from a dictionary as shown below.

```python
pensieve['integers']
# output: [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

pensieve['even_integers']
# output: [0, 2, 4, 6, 8]

```


### Changing a Memory
When you change a memory in pensieve, all **successors** get notified and marked as *stale* but not updated immediately.
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
